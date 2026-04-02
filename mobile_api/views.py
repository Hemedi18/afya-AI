import json
from os.path import basename
from pathlib import Path

from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db.models import Q

from chats.models import PrivateConversation, PrivateMessage
from users.permissions import is_admin

from .models import MobileAuthToken


User = get_user_model()

MAX_ATTACHMENT_MB = 100  # Increased from 20MB to 100MB for better UX
ALLOWED_ATTACHMENT_EXTENSIONS = {
    'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg',
    'mp4', 'mov', 'webm', 'avi', 'mkv', 'flv', 'wmv',
    'pdf', 'doc', 'docx', 'txt', 'xls', 'xlsx', 'ppt', 'pptx', 'zip', 'rar', 'odt', 'rtf',
}


def _json_body(request):
    try:
        return json.loads(request.body.decode('utf-8') or '{}')
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def _token_from_request(request):
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Token '):
        return auth_header.split(' ', 1)[1].strip()
    return ''


def _mobile_user(request):
    key = _token_from_request(request)
    if not key:
        return None, None
    token = MobileAuthToken.objects.select_related('user').filter(key=key, is_active=True).first()
    if not token:
        return None, None
    if token.is_expired:
        token.is_active = False
        token.save(update_fields=['is_active'])
        return None, None
    token.touch()
    return token.user, token


def _validate_attachment(attachment):
    if not attachment:
        return None
    
    # Validate file name exists
    if not attachment.name:
        return 'Attachment missing filename'
    
    # Get extension safely
    ext = Path(attachment.name).suffix.lower().lstrip('.')
    if not ext or ext not in ALLOWED_ATTACHMENT_EXTENSIONS:
        return f'File type .{ext} not allowed'
    
    # Validate file size
    if not hasattr(attachment, 'size') or attachment.size is None:
        return 'Unable to determine file size'
    
    size_mb = attachment.size / (1024 * 1024)
    if size_mb > MAX_ATTACHMENT_MB:
        return f'Faili ni kubwa. Max {MAX_ATTACHMENT_MB}MB, Yako: {size_mb:.1f}MB'
    
    # Minimum file size check (at least 1KB)
    if attachment.size < 1024:
        return 'Faili ni ndogo sana (minimum 1KB)'
    
    return None


def _serialize_message(msg):
    return {
        'id': msg.id,
        'sender_id': msg.sender_id,
        'sender_name': msg.sender.get_full_name() or msg.sender.username,
        'content': msg.content,
        'has_attachment': bool(msg.attachment),
        'attachment_url': msg.attachment.url if msg.attachment else None,
        'attachment_name': basename(msg.attachment.name) if msg.attachment else '',
        'is_read': bool(msg.is_read),
        'created_at': msg.created_at.isoformat(),
    }


class MobileAuthRequiredView(View):
    user = None
    token = None

    def dispatch(self, request, *args, **kwargs):
        user, token = _mobile_user(request)
        if not user:
            return JsonResponse({'ok': False, 'error': 'Unauthorized'}, status=401)
        self.user = user
        self.token = token
        return super().dispatch(request, *args, **kwargs)


@method_decorator(csrf_exempt, name='dispatch')
class MobileLoginApiView(View):
    def post(self, request, *args, **kwargs):
        data = _json_body(request)
        username = (data.get('username') or '').strip()
        password = data.get('password') or ''
        if not username or not password:
            return JsonResponse({'ok': False, 'error': 'username and password are required'}, status=400)

        user = authenticate(request, username=username, password=password)
        if not user:
            return JsonResponse({'ok': False, 'error': 'Invalid credentials'}, status=401)

        token = MobileAuthToken.issue_for_user(user)
        return JsonResponse(
            {
                'ok': True,
                'token': token.key,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'full_name': user.get_full_name() or user.username,
                    'email': user.email,
                },
            }
        )


@method_decorator(csrf_exempt, name='dispatch')
class MobileRegisterApiView(View):
    def post(self, request, *args, **kwargs):
        data = _json_body(request)
        username = (data.get('username') or '').strip()
        password = data.get('password') or ''
        email = (data.get('email') or '').strip()
        first_name = (data.get('first_name') or '').strip()
        last_name = (data.get('last_name') or '').strip()

        if not username or not password:
            return JsonResponse({'ok': False, 'error': 'username and password are required'}, status=400)
        if len(password) < 6:
            return JsonResponse({'ok': False, 'error': 'password must be at least 6 chars'}, status=400)
        if User.objects.filter(username=username).exists():
            return JsonResponse({'ok': False, 'error': 'username already exists'}, status=400)

        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name,
        )
        token = MobileAuthToken.issue_for_user(user)
        return JsonResponse(
            {
                'ok': True,
                'token': token.key,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'full_name': user.get_full_name() or user.username,
                    'email': user.email,
                },
            }
        )


@method_decorator(csrf_exempt, name='dispatch')
class MobileLogoutApiView(MobileAuthRequiredView):
    def post(self, request, *args, **kwargs):
        self.token.is_active = False
        self.token.save(update_fields=['is_active'])
        return JsonResponse({'ok': True})


class MobileMeApiView(MobileAuthRequiredView):
    def get(self, request, *args, **kwargs):
        return JsonResponse(
            {
                'ok': True,
                'user': {
                    'id': self.user.id,
                    'username': self.user.username,
                    'full_name': self.user.get_full_name() or self.user.username,
                    'email': self.user.email,
                },
            }
        )


class MobileConversationListApiView(MobileAuthRequiredView):
    def get(self, request, *args, **kwargs):
        qs = PrivateConversation.objects.filter(
            Q(patient=self.user) | Q(doctor=self.user)
        ).select_related('patient', 'doctor').prefetch_related('messages__sender')

        items = []
        for convo in qs:
            other = convo.doctor if convo.patient_id == self.user.id else convo.patient
            last_message = convo.messages.last()
            unread_count = convo.messages.filter(is_read=False).exclude(sender=self.user).count()
            items.append(
                {
                    'id': convo.id,
                    'subject': convo.subject,
                    'updated_at': convo.updated_at.isoformat(),
                    'other_user': {
                        'id': other.id,
                        'username': other.username,
                        'full_name': other.get_full_name() or other.username,
                    },
                    'unread_count': unread_count,
                    'last_message': _serialize_message(last_message) if last_message else None,
                }
            )

        return JsonResponse({'ok': True, 'items': items})


@method_decorator(csrf_exempt, name='dispatch')
class MobileStartConversationApiView(MobileAuthRequiredView):
    def post(self, request, *args, **kwargs):
        data = _json_body(request)
        doctor_username = (data.get('doctor_username') or '').strip()
        subject = (data.get('subject') or '').strip()
        opening_message = (data.get('opening_message') or '').strip()

        if not doctor_username or not subject or not opening_message:
            return JsonResponse(
                {'ok': False, 'error': 'doctor_username, subject and opening_message are required'},
                status=400,
            )

        doctor = User.objects.filter(username=doctor_username).first()
        if not doctor:
            return JsonResponse({'ok': False, 'error': 'Doctor username not found'}, status=404)

        doctor_profile = getattr(doctor, 'doctor_profile', None)
        if not doctor_profile or not doctor_profile.verified:
            return JsonResponse({'ok': False, 'error': 'Doctor is not verified yet'}, status=400)

        convo = PrivateConversation.objects.create(
            patient=self.user,
            doctor=doctor,
            subject=subject,
        )
        first_msg = PrivateMessage.objects.create(
            conversation=convo,
            sender=self.user,
            content=opening_message,
        )

        return JsonResponse(
            {
                'ok': True,
                'conversation': {
                    'id': convo.id,
                    'subject': convo.subject,
                    'other_user': {
                        'id': doctor.id,
                        'username': doctor.username,
                        'full_name': doctor.get_full_name() or doctor.username,
                    },
                    'last_message': _serialize_message(first_msg),
                },
            }
        )


@method_decorator(csrf_exempt, name='dispatch')
class MobileConversationDetailApiView(MobileAuthRequiredView):
    def _conversation(self, conversation_id):
        convo = get_object_or_404(
            PrivateConversation.objects.select_related('patient', 'doctor').prefetch_related('messages__sender'),
            pk=conversation_id,
        )
        if not (is_admin(self.user) or self.user in [convo.patient, convo.doctor]):
            return None
        return convo

    def get(self, request, conversation_id, *args, **kwargs):
        convo = self._conversation(conversation_id)
        if not convo:
            return JsonResponse({'ok': False, 'error': 'No permission'}, status=403)

        since = request.GET.get('since', '0')
        try:
            since_id = int(since)
        except ValueError:
            since_id = 0

        qs = convo.messages.filter(id__gt=since_id).select_related('sender').order_by('id')
        qs.exclude(sender=self.user).update(is_read=True)
        return JsonResponse({'ok': True, 'items': [_serialize_message(m) for m in qs]})

    def post(self, request, conversation_id, *args, **kwargs):
        convo = self._conversation(conversation_id)
        if not convo:
            return JsonResponse({'ok': False, 'error': 'No permission'}, status=403)

        content = (request.POST.get('content') or '').strip()
        attachment = request.FILES.get('attachment')
        attachment_error = _validate_attachment(attachment)
        if attachment_error:
            return JsonResponse({'ok': False, 'error': attachment_error}, status=400)
        if not content and not attachment:
            return JsonResponse({'ok': False, 'error': 'content or attachment is required'}, status=400)

        msg = PrivateMessage.objects.create(
            conversation=convo,
            sender=self.user,
            content=content or ' ',
            attachment=attachment,
        )
        convo.save(update_fields=['updated_at'])
        return JsonResponse({'ok': True, 'item': _serialize_message(msg)})
