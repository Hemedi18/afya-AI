import base64
import json
import re
import uuid
from urllib.parse import urlencode
from os.path import basename

import bleach
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.paginator import Paginator
from django.db.models import Count, ExpressionWrapper, F, IntegerField, Prefetch, Q
from django.http import JsonResponse
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.translation import gettext as _
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from bleach.css_sanitizer import CSSSanitizer

from menstrual.models import (
	CommunityGroup,
	CommunityGroupJoinRequest,
	CommunityPost,
	CommunityPostMedia,
	CommunityReply,
	CommunityStatus,
	CommunityStatusComment,
	CommunityStatusMedia,
	CommunityStatusShare,
	MenstrualUserSetting,
)
from users.permissions import DoctorRequiredMixin, ModeratorRequiredMixin, can_moderate, is_admin, is_doctor
from users.utils import get_user_gender

from .forms import (
	ClarificationRequestForm,
	CommunityGroupForm,
	CommunityStatusForm,
	ContentReportForm,
	PrivateConversationStartForm,
	PrivateMessageForm,
)
from .models import ClarificationMessage, ClarificationRequest, ContentReport, PrivateConversation, PrivateMessage
from users.models import UserAIPersona


def _audience_for_user(user):
	user_gender = get_user_gender(user)
	return CommunityPost.AUDIENCE_MALE if user_gender == 'male' else CommunityPost.AUDIENCE_FEMALE


def _avatar_url_for(user):
	persona = getattr(user, 'ai_persona', None)
	avatar = getattr(persona, 'avatar', None) if persona else None
	if not avatar:
		return ''
	try:
		if not avatar.name or not avatar.storage.exists(avatar.name):
			return ''
		return avatar.url
	except (ValueError, OSError):
		return ''


def _prepare_user_avatar(user):
	user.community_avatar_url = _avatar_url_for(user)
	user.community_avatar_initial = (getattr(user, 'username', '')[:1] or '?').upper()
	return user


def _verified_doctors_queryset():
	return User.objects.filter(
		doctor_profile__verified=True,
	).select_related('doctor_profile', 'ai_persona').order_by('first_name', 'username')


def _resolve_target_doctor(target_role, doctor_id):
	if target_role != ClarificationRequest.TARGET_DOCTOR:
		return None
	if not doctor_id or not str(doctor_id).isdigit():
		return None
	return _verified_doctors_queryset().filter(pk=doctor_id).first()


def _is_regular_user(user):
	return not (is_admin(user) or is_doctor(user) or can_moderate(user))


def _get_ai_suggested_groups(user, base_groups_qs):
	"""Return AI-suggested groups annotated with member count, ranked by relevance to user data."""
	# Gather user health context
	try:
		persona = user.ai_persona
	except Exception:
		persona = None

	gender = get_user_gender(user)
	health_text = ''
	if persona:
		health_text = ' '.join(filter(None, [
			persona.health_notes or '',
			persona.permanent_diseases or '',
			persona.lifestyle_notes or '',
			persona.goals or '',
			persona.mental_health or '',
		])).lower()

	# Keyword relevance scoring
	FEMALE_KEYWORDS = ['menstrual', 'hedhi', 'ujauzito', 'pregnancy', 'mama', 'ovulation',
	                   'wanawake', 'kujifungua', 'breastfeed', 'uzazi', 'uzito wa mama',
	                   'birth', 'kipindi', 'mzunguko', 'reproductive', 'gynec']
	MALE_KEYWORDS    = ['wanaume', 'prostate', 'fertility men', 'afya ya wanaume', 'testosterone']
	HEALTH_KEYWORDS  = ['diabetes', 'sukari', 'moyo', 'heart', 'shinikizo', 'blood pressure',
	                    'malaria', 'cancer', 'saratani', 'mental', 'akili', 'anxiety',
	                    'depression', 'nutrition', 'lishe', 'exercise', 'mazoezi', 'weight',
	                    'uzito', 'obesity', 'asthma', 'pumu', 'kidney', 'figo', 'liver']

	groups = list(base_groups_qs.annotate(member_total=Count('members', distinct=True)))

	def score_group(group):
		name_lower = group.name.lower()
		desc_lower = (group.description or '').lower()
		group_text = name_lower + ' ' + desc_lower
		score = 0
		# Gender-based boost
		if gender == 'female':
			for kw in FEMALE_KEYWORDS:
				if kw in group_text:
					score += 3
		elif gender == 'male':
			for kw in MALE_KEYWORDS:
				if kw in group_text:
					score += 3
		# Health notes match
		for kw in HEALTH_KEYWORDS:
			if kw in health_text and kw in group_text:
				score += 2
		# Popularity boost (log scale)
		score += min(group.member_total // 5, 5)
		return score

	groups.sort(key=score_group, reverse=True)
	return groups[:8]


RICH_TEXT_ALLOWED_TAGS = [
	'p', 'br', 'div', 'span', 'strong', 'b', 'em', 'i', 'u', 's',
	'ul', 'ol', 'li', 'blockquote', 'a', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
]
RICH_TEXT_ALLOWED_ATTRIBUTES = {
	'*': ['style'],
	'a': ['href', 'title', 'target', 'rel'],
}
RICH_TEXT_CSS = CSSSanitizer(
	allowed_css_properties=[
		'color', 'background-color', 'font-size', 'font-weight', 'font-style',
		'text-decoration', 'text-align', 'font-family',
	]
)


def _sanitize_rich_content(content):
	cleaned = bleach.clean(
		content or '',
		tags=RICH_TEXT_ALLOWED_TAGS,
		attributes=RICH_TEXT_ALLOWED_ATTRIBUTES,
		css_sanitizer=RICH_TEXT_CSS,
		strip=True,
	)
	return bleach.linkify(cleaned)


def _content_file_from_data_url(data_url):
	if not data_url or ';base64,' not in data_url:
		return None
	format_part, encoded = data_url.split(';base64,', 1)
	extension = format_part.split('/')[-1].lower()
	if extension == 'jpeg':
		extension = 'jpg'
	try:
		decoded = base64.b64decode(encoded)
	except (ValueError, TypeError):
		return None
	return ContentFile(decoded, name=f"post-crop-{uuid.uuid4().hex}.{extension}")


def _prepare_post_preview(post, preview_words=42):
	plain_content = strip_tags(post.content or '').strip()
	words = plain_content.split()
	post.preview_text = ' '.join(words[:preview_words])
	post.has_more_content = len(words) > preview_words
	post.word_count = len(words)
	return post


def _select_featured_comment(post):
	top_level_comments = [reply for reply in post.replies.all() if not reply.parent_id]
	if not top_level_comments:
		post.featured_comment = None
		post.hidden_comment_count = 0
		return post
	post.featured_comment = max(
		top_level_comments,
		key=lambda reply: (
			reply.child_replies.count(),
			reply.likes.count(),
			reply.created_at,
		),
	)
	post.hidden_comment_count = max(len(top_level_comments) - 1, 0)
	return post


def _prepare_posts_for_feed(posts):
	for post in posts:
		_prepare_post_preview(post)
		_select_featured_comment(post)
	return posts


def _related_posts_for(post, limit=8):
	def _tokens(value):
		words = re.findall(r"[\w']+", strip_tags(value or '').lower())
		return {w for w in words if len(w) >= 4}

	base_tokens = _tokens(post.content)
	if len(base_tokens) > 14:
		base_tokens = set(list(base_tokens)[:14])

	candidates = list(
		CommunityPost.objects.select_related('user', 'group').prefetch_related('groups', 'media_items').filter(
			audience_gender=post.audience_gender,
		).exclude(pk=post.pk).order_by('-created_at')[:90]
	)

	scored = []
	for candidate in candidates:
		score = 0
		if candidate.user_id == post.user_id:
			score += 120
		if post.group_id and candidate.group_id == post.group_id:
			score += 25
		if post.group_id and candidate.groups.filter(pk=post.group_id).exists():
			score += 18
		if post.groups.exists() and candidate.group_id and post.groups.filter(pk=candidate.group_id).exists():
			score += 14
		common = len(base_tokens.intersection(_tokens(candidate.content))) if base_tokens else 0
		score += common * 3
		if score > 0:
			scored.append((score, candidate.created_at, candidate))

	if scored:
		scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
		return [item[2] for item in scored[:limit]]

	return candidates[:limit]


def _community_post_form_context(user, selected_group_id=None):
	audience_gender = _audience_for_user(user)
	groups = CommunityGroup.objects.filter(audience_gender=audience_gender).prefetch_related('members')
	selected_group = None
	selected_group_ids = []
	if selected_group_id and str(selected_group_id).isdigit():
		selected_group = groups.filter(pk=selected_group_id).first()
		if selected_group:
			selected_group_ids = [selected_group.id]
	all_doctors = [_prepare_user_avatar(doctor) for doctor in _verified_doctors_queryset().exclude(pk=user.pk)]
	settings_obj, _ = MenstrualUserSetting.objects.get_or_create(user=user)
	user_gender = get_user_gender(user)
	return {
		'groups': groups,
		'selected_group': selected_group,
		'selected_group_ids': selected_group_ids,
		'available_doctors': all_doctors,
		'default_anonymous_mode': settings_obj.anonymous_mode,
		'community_gender_label': 'Wanawake' if user_gender == 'female' else 'Wanaume' if user_gender == 'male' else 'General',
	}


def _can_respond_to_clarification(user, clarification):
	if not user.is_authenticated:
		return False
	if clarification.target_role == ClarificationRequest.TARGET_ADMIN:
		return is_admin(user)
	if clarification.target_role == ClarificationRequest.TARGET_DOCTOR:
		if not (is_doctor(user) or is_admin(user)):
			return False
		if clarification.target_doctor_id and clarification.target_doctor_id != user.id and not is_admin(user):
			return False
		return True
	if clarification.target_role == ClarificationRequest.TARGET_GROUP_ADMIN:
		if is_admin(user):
			return True
		if clarification.group_id and clarification.group and clarification.group.created_by_id == user.id:
			return True
		return False
	return False


def _can_participate_in_clarification(user, clarification):
	if not user.is_authenticated:
		return False
	if clarification.asker_id == user.id or clarification.responded_by_id == user.id:
		return True
	return _can_respond_to_clarification(user, clarification)


def _prepare_clarification_threads(user, clarifications, focused_clarification_id=None):
	for clarification in clarifications:
		clarification.can_user_respond = _can_respond_to_clarification(user, clarification)
		clarification.can_user_participate = _can_participate_in_clarification(user, clarification)
		clarification.is_focused = clarification.id == focused_clarification_id
	return clarifications


def _notification_context_for_user(user, limit=5):
	recent_comment_notifications = CommunityReply.objects.select_related('user', 'post').filter(
		post__user=user,
	).exclude(user=user).order_by('-created_at')[:limit]

	recent_clarification_answers = ClarificationRequest.objects.select_related('responded_by', 'post', 'comment').filter(
		asker=user,
		status=ClarificationRequest.STATUS_ANSWERED,
	).exclude(response='').order_by('-updated_at')[:limit]

	recent_clarification_requests = ClarificationRequest.objects.select_related('post', 'comment').filter(
		asker=user,
	).order_by('-created_at')[:limit]

	recent_report_updates = ContentReport.objects.select_related('reviewed_by', 'post', 'comment').filter(
		reporter=user,
	).exclude(status=ContentReport.STATUS_OPEN).order_by('-created_at')[:limit]

	recent_group_join_approvals = CommunityGroupJoinRequest.objects.select_related('group').filter(
		user=user,
		status=CommunityGroupJoinRequest.STATUS_APPROVED,
		is_notified=False,
	).order_by('-updated_at')[:limit]

	unread_private_count = PrivateMessage.objects.filter(
		Q(conversation__patient=user) | Q(conversation__doctor=user),
		is_read=False,
	).exclude(sender=user).count()

	return {
		'recent_comment_notifications': recent_comment_notifications,
		'recent_clarification_answers': recent_clarification_answers,
		'recent_clarification_requests': recent_clarification_requests,
		'recent_report_updates': recent_report_updates,
		'recent_group_join_approvals': recent_group_join_approvals,
		'unread_private_count': unread_private_count,
	}


def _serialize_private_message(msg):
	return {
		'id': msg.id,
		'sender_id': msg.sender_id,
		'sender_name': msg.sender.get_full_name() or msg.sender.username,
		'content': msg.content,
		'has_attachment': bool(msg.attachment),
		'attachment_url': msg.attachment.url if msg.attachment else None,
		'attachment_name': basename(msg.attachment.name) if msg.attachment else '',
		'is_read': bool(msg.is_read),
		'created_at': msg.created_at.strftime('%d %b %Y %H:%M'),
	}


CALL_SIGNAL_EVENTS = {'call_invite', 'call_accept', 'call_reject', 'call_end', 'call_busy'}


def _call_events_cache_key(user_id, conversation_id):
	return f'private_call_events:{conversation_id}:{user_id}'


def _global_call_events_cache_key(user_id):
	return f'private_call_events_global:{user_id}'


def _queue_private_call_event(recipient_id, conversation_id, payload):
	key = _call_events_cache_key(recipient_id, conversation_id)
	events = cache.get(key, [])
	events.append(payload)
	cache.set(key, events[-25:], timeout=120)

	global_key = _global_call_events_cache_key(recipient_id)
	global_events = cache.get(global_key, [])
	global_events.append(payload)
	cache.set(global_key, global_events[-60:], timeout=180)


def _pop_private_call_events(user_id, conversation_id):
	key = _call_events_cache_key(user_id, conversation_id)
	events = cache.get(key, [])
	cache.delete(key)
	return events


def _pop_global_private_call_events(user_id):
	key = _global_call_events_cache_key(user_id)
	events = cache.get(key, [])
	cache.delete(key)
	return events


class SocialFeedView(LoginRequiredMixin, View):
	template_name = 'chats/feed.html'

	def get(self, request, *args, **kwargs):
		active_section = kwargs.get('section', 'posts')
		if active_section not in {'groups', 'posts', 'status', 'private'}:
			active_section = 'posts'

		user_gender = get_user_gender(request.user)
		audience_gender = _audience_for_user(request.user)
		default_group_name = 'General Men' if audience_gender == CommunityPost.AUDIENCE_MALE else 'General Women'
		default_group, _ = CommunityGroup.objects.get_or_create(
			name=default_group_name,
			audience_gender=audience_gender,
			defaults={'description': 'Group kuu la jamii.', 'created_by': request.user},
		)
		default_group.members.add(request.user)

		groups = CommunityGroup.objects.filter(audience_gender=audience_gender).prefetch_related('members')
		all_doctors = [_prepare_user_avatar(doctor) for doctor in _verified_doctors_queryset().exclude(pk=request.user.pk)]
		suggested_doctors = all_doctors[:5]
		selected_group_id = request.GET.get('group')
		selected_group = None
		if selected_group_id and str(selected_group_id).isdigit():
			selected_group = groups.filter(pk=selected_group_id).first()
		if not selected_group:
			selected_group = default_group

		posts_qs = CommunityPost.objects.select_related('user', 'group').prefetch_related(
			'groups',
			'media_items',
			'replies__user',
			'replies__likes',
			'replies__dislikes',
			'replies__child_replies__user',
			'replies__clarifications__responded_by',
			'replies__clarifications__target_doctor',
			'likes',
			'clarifications__responded_by',
			'clarifications__target_doctor',
		)
		if user_gender in {'female', 'male'}:
			posts_qs = posts_qs.filter(audience_gender=user_gender)
		# Apply strict group filter only when user explicitly selected a group.
		# By default, show all posts in the current gender audience.
		if selected_group_id and selected_group and active_section != 'private':
			posts_qs = posts_qs.filter(
				Q(group=selected_group)
				| Q(groups=selected_group)
				| Q(group__isnull=True, groups__isnull=True)
			).distinct()
		posts = posts_qs.order_by('-created_at')
		private_posts = posts_qs.order_by('-created_at') if active_section == 'private' else None
		recent_posts = posts[:5]
		paginator = Paginator(posts, 10)
		page_number = request.GET.get('page')
		posts_page = paginator.get_page(page_number)
		_prepare_posts_for_feed(posts_page.object_list)

		statuses = list(CommunityStatus.objects.select_related('user', 'group').prefetch_related('media_items').filter(
			audience_gender=audience_gender,
			expires_at__gt=timezone.now(),
		).annotate(
			likes_total=Count('likes', distinct=True),
			comments_total=Count('comments', distinct=True),
			shares_total=Count('shares', distinct=True),
			rating_score=ExpressionWrapper(
				(F('likes_total') * 4) + (F('comments_total') * 3) + (F('shares_total') * 5),
				output_field=IntegerField(),
			),
		).order_by('-rating_score', '-created_at')[:30])

		groups_for_inline = _get_ai_suggested_groups(request.user, groups)
		notification_context = _notification_context_for_user(request.user, limit=5)

		settings_obj, _ = MenstrualUserSetting.objects.get_or_create(user=request.user)
		return render(
			request,
			self.template_name,
			{
				'posts': posts_page,
				'recent_posts': recent_posts,
				'private_posts': private_posts,
				'active_section': active_section,
				'groups': groups,
				'suggested_doctors': suggested_doctors,
				'available_doctors': all_doctors,
				'selected_group': selected_group,
				'statuses': statuses,
				'status_featured': statuses[:12],
				'group_form': CommunityGroupForm(),
				'status_form': CommunityStatusForm(initial={'group_id': selected_group.id if selected_group else None}),
				'clarification_form': ClarificationRequestForm(),
				'can_moderate': can_moderate(request.user),
				'default_anonymous_mode': settings_obj.anonymous_mode,
				'community_gender': user_gender,
				'community_gender_label': 'Wanawake' if user_gender == 'female' else 'Wanaume' if user_gender == 'male' else 'General',
				'my_group_ids': set(request.user.community_groups.values_list('id', flat=True)),
				**notification_context,
				'posts_count': posts_qs.count(),
				'is_moderator_user': can_moderate(request.user),
				'is_admin_user': is_admin(request.user),
				'is_doctor_user': is_doctor(request.user),
				'is_regular_user': _is_regular_user(request.user),
				'groups_for_inline': groups_for_inline,
			},
		)


class NotificationsView(LoginRequiredMixin, View):
	template_name = 'chats/notifications.html'

	def get(self, request, *args, **kwargs):
		context = _notification_context_for_user(request.user, limit=40)
		approval_ids = [item.id for item in context.get('recent_group_join_approvals', [])]
		if approval_ids:
			CommunityGroupJoinRequest.objects.filter(id__in=approval_ids).update(is_notified=True)
		return render(request, self.template_name, context)


class PostDetailView(LoginRequiredMixin, View):
	template_name = 'chats/post_detail.html'

	def get(self, request, post_id, *args, **kwargs):
		focused_clarification_id = request.GET.get('clarification')
		focused_clarification_id = int(focused_clarification_id) if str(focused_clarification_id).isdigit() else None
		comment_sort = (request.GET.get('comments') or 'recent').lower()
		child_reply_qs = CommunityReply.objects.select_related('user').prefetch_related(
			'clarifications__responded_by',
			'clarifications__target_doctor',
			'clarifications__messages__user',
			'clarifications__likes',
			'clarifications__dislikes',
		).order_by('created_at')
		post = get_object_or_404(
			CommunityPost.objects.select_related('user', 'group').prefetch_related(
				'groups',
				'media_items',
				'replies__user',
				'replies__likes',
				'replies__dislikes',
				Prefetch('replies__child_replies', queryset=child_reply_qs),
				'replies__clarifications__responded_by',
				'replies__clarifications__target_doctor',
				'replies__clarifications__messages__user',
				'replies__clarifications__likes',
				'replies__clarifications__dislikes',
				'likes',
				'clarifications__responded_by',
				'clarifications__target_doctor',
				'clarifications__messages__user',
				'clarifications__likes',
				'clarifications__dislikes',
			),
			pk=post_id,
		)
		user_gender = get_user_gender(request.user)
		if user_gender in {'female', 'male'} and post.audience_gender != user_gender:
			messages.error(request, 'Huna ruhusa kuona post hii.')
			return redirect('chats:feed')
		related_posts = _related_posts_for(post, limit=8)
		_prepare_posts_for_feed(related_posts)
		available_doctors = [_prepare_user_avatar(doctor) for doctor in _verified_doctors_queryset().exclude(pk=request.user.pk)]
		_prepare_clarification_threads(request.user, list(post.clarifications.all()), focused_clarification_id)

		top_level_comments = CommunityReply.objects.filter(post=post, parent__isnull=True).select_related('user').prefetch_related(
			'likes',
			'dislikes',
			Prefetch('child_replies', queryset=child_reply_qs),
			'clarifications__responded_by',
			'clarifications__target_doctor',
			'clarifications__messages__user',
			'clarifications__likes',
			'clarifications__dislikes',
		).annotate(
			likes_total=Count('likes', distinct=True),
			replies_total=Count('child_replies', distinct=True),
		)
		if comment_sort == 'likes':
			top_level_comments = top_level_comments.order_by('-likes_total', '-created_at')
		elif comment_sort in {'reviews', 'replies'}:
			top_level_comments = top_level_comments.order_by('-replies_total', '-created_at')
		elif comment_sort == 'oldest':
			top_level_comments = top_level_comments.order_by('created_at')
		else:
			comment_sort = 'recent'
			top_level_comments = top_level_comments.order_by('-created_at')
		for reply in top_level_comments:
			_prepare_clarification_threads(request.user, list(reply.clarifications.all()), focused_clarification_id)
			for child in reply.child_replies.all():
				_prepare_clarification_threads(request.user, list(child.clarifications.all()), focused_clarification_id)
		return render(
			request,
			self.template_name,
			{
				'post': post,
				'can_moderate': can_moderate(request.user),
				'related_posts': related_posts,
				'available_doctors': available_doctors,
				'top_level_comments': top_level_comments,
				'focused_clarification_id': focused_clarification_id,
				'comment_sort': comment_sort,
			},
		)


class CommunityUserProfileView(LoginRequiredMixin, View):
	template_name = 'chats/user_profile.html'

	def get(self, request, user_id, *args, **kwargs):
		target_user = get_object_or_404(User, pk=user_id)
		user_gender = get_user_gender(request.user)
		audience_gender = _audience_for_user(request.user)

		posts_qs = CommunityPost.objects.select_related('group').prefetch_related('groups').filter(user=target_user)
		if user_gender in {'female', 'male'}:
			posts_qs = posts_qs.filter(audience_gender=audience_gender)
		posts = posts_qs.order_by('-created_at')
		total_posts = posts.count()
		total_comments = CommunityReply.objects.filter(user=target_user).count()
		total_likes_received = sum(post.likes.count() for post in posts)

		return render(
			request,
			self.template_name,
			{
				'target_user': target_user,
				'posts': posts,
				'total_posts': total_posts,
				'total_comments': total_comments,
				'total_likes_received': total_likes_received,
			},
		)


class CreatePostView(LoginRequiredMixin, View):
	template_name = 'chats/create_post.html'

	def get(self, request, *args, **kwargs):
		persona, _ = UserAIPersona.objects.get_or_create(user=request.user)
		profile_complete = persona.profile_completeness_score >= 100
		settings_obj, _ = MenstrualUserSetting.objects.get_or_create(user=request.user)
		
		context = _community_post_form_context(request.user, request.GET.get('group'))
		context['persona'] = persona
		context['profile_complete'] = profile_complete
		context['profile_completeness'] = persona.profile_completeness_score
		context['default_anonymous_mode'] = settings_obj.anonymous_mode
		context['onboarding_next_url'] = request.get_full_path()
		return render(request, self.template_name, context)

	def post(self, request, *args, **kwargs):
		persona, _ = UserAIPersona.objects.get_or_create(user=request.user)
		settings_obj, _ = MenstrualUserSetting.objects.get_or_create(user=request.user)
		per_post_anon = request.POST.get('is_anonymous') == 'on'
		is_anonymous = settings_obj.anonymous_mode or per_post_anon
		profile_incomplete = persona.profile_completeness_score < 100
		terms_accepted = request.POST.get('terms_accepted') == 'on'
		group_id = request.POST.get('group') or request.GET.get('group')
		base_next = reverse('chats:post_create')
		if group_id and str(group_id).isdigit():
			base_next = f"{base_next}?{urlencode({'group': group_id})}"
		
		if profile_incomplete and not is_anonymous:
			messages.error(request, f'Kamilizia profile yako 100% kabla ya kupost. (Sasa {persona.profile_completeness_score}%)')
			onboarding_url = f"{reverse('users:onboarding', kwargs={'step': 1})}?{urlencode({'next': base_next})}"
			return redirect(onboarding_url)
		
		if not terms_accepted:
			messages.error(request, 'Tafadhali bali terms na conditions kabla ya kupost.')
			return redirect(base_next)
		
		raw_content = request.POST.get('content') or ''
		content = _sanitize_rich_content(raw_content)
		plain_content = strip_tags(content).strip()
		cropped_image = _content_file_from_data_url(request.POST.get('cropped_image_data'))
		image = cropped_image or request.FILES.get('image')
		video = request.FILES.get('video')
		media_files = request.FILES.getlist('media_files')
		group_ids = [group_id for group_id in request.POST.getlist('group_ids') if str(group_id).isdigit()]
		post_for_all = request.POST.get('post_for_all') == 'on'
		publish_as_status = request.POST.get('publish_as_status') == 'on'
		audience_gender = _audience_for_user(request.user)
		media_ratio = (request.POST.get('media_ratio') or 'auto')[:20]
		media_shape = (request.POST.get('media_shape') or 'rounded')[:20]
		try:
			media_focus_x = max(0, min(100, int(request.POST.get('media_focus_x') or 50)))
			media_focus_y = max(0, min(100, int(request.POST.get('media_focus_y') or 50)))
		except ValueError:
			media_focus_x, media_focus_y = 50, 50

		selected_groups = list(CommunityGroup.objects.filter(pk__in=group_ids, audience_gender=audience_gender).prefetch_related('members'))
		for group in selected_groups:
			if not group.members.filter(pk=request.user.pk).exists():
				messages.warning(request, f'Jiunge kwanza kwenye group ya {group.name} kabla ya kupost.')
				return redirect('chats:post_create')

		primary_group = None if post_for_all else (selected_groups[0] if selected_groups else None)

		if image and video and not media_files:
			messages.warning(request, 'Chagua image au video moja kwa post moja.')
			return redirect('chats:post_create')
		if not plain_content and not image and not video and not media_files:
			messages.warning(request, 'Andika ujumbe au ongeza image/video kabla ya kutuma post.')
			return redirect('chats:post_create')
		if len(media_files) > 8:
			messages.warning(request, 'Unaweza kuongeza media hadi 8 kwa post moja.')
			return redirect('chats:post_create')

		new_post = CommunityPost.objects.create(
			user=request.user,
			group=primary_group,
			content=content or plain_content or ' ',
			image=image,
			video=video,
			media_ratio=media_ratio,
			media_shape=media_shape,
			media_focus_x=media_focus_x,
			media_focus_y=media_focus_y,
			is_anonymous=is_anonymous,
			audience_gender=audience_gender,
		)
		if selected_groups:
			new_post.groups.set(selected_groups)

		if media_files:
			for idx, mf in enumerate(media_files):
				content_type = (getattr(mf, 'content_type', '') or '').lower()
				name_l = (getattr(mf, 'name', '') or '').lower()
				is_image = content_type.startswith('image/') or name_l.endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif'))
				is_video = content_type.startswith('video/') or name_l.endswith(('.mp4', '.mov', '.webm', '.mkv', '.avi'))
				if not (is_image or is_video):
					continue
				CommunityPostMedia.objects.create(
					post=new_post,
					media_type=CommunityPostMedia.MEDIA_IMAGE if is_image else CommunityPostMedia.MEDIA_VIDEO,
					image=mf if is_image else None,
					video=mf if is_video else None,
					sort_order=idx,
				)

		if publish_as_status:
			status_text = strip_tags(content).strip()[:250]
			status_primary_image = image
			if media_files and not status_primary_image:
				for mf in media_files:
					ctype = (getattr(mf, 'content_type', '') or '').lower()
					if ctype.startswith('image/'):
						status_primary_image = mf
						break
			if selected_groups and not post_for_all:
				for group in selected_groups:
					status_obj = CommunityStatus.objects.create(
						user=request.user,
						group=group,
						audience_gender=audience_gender,
						content=status_text or 'Status mpya',
						image=status_primary_image,
					)
					if media_files:
						for idx, mf in enumerate(media_files):
							content_type = (getattr(mf, 'content_type', '') or '').lower()
							name_l = (getattr(mf, 'name', '') or '').lower()
							is_image = content_type.startswith('image/') or name_l.endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif'))
							is_video = content_type.startswith('video/') or name_l.endswith(('.mp4', '.mov', '.webm', '.mkv', '.avi'))
							if not (is_image or is_video):
								continue
							CommunityStatusMedia.objects.create(
								status=status_obj,
								media_type=CommunityStatusMedia.MEDIA_IMAGE if is_image else CommunityStatusMedia.MEDIA_VIDEO,
								image=mf if is_image else None,
								video=mf if is_video else None,
								sort_order=idx,
							)
			else:
				status_obj = CommunityStatus.objects.create(
					user=request.user,
					group=None,
					audience_gender=audience_gender,
					content=status_text or 'Status mpya',
					image=status_primary_image,
				)
				if media_files:
					for idx, mf in enumerate(media_files):
						content_type = (getattr(mf, 'content_type', '') or '').lower()
						name_l = (getattr(mf, 'name', '') or '').lower()
						is_image = content_type.startswith('image/') or name_l.endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif'))
						is_video = content_type.startswith('video/') or name_l.endswith(('.mp4', '.mov', '.webm', '.mkv', '.avi'))
						if not (is_image or is_video):
							continue
						CommunityStatusMedia.objects.create(
							status=status_obj,
							media_type=CommunityStatusMedia.MEDIA_IMAGE if is_image else CommunityStatusMedia.MEDIA_VIDEO,
							image=mf if is_image else None,
							video=mf if is_video else None,
							sort_order=idx,
						)

		request_clarification = request.POST.get('request_clarification') == 'on'
		clarify_target_role = request.POST.get('clarify_target_role')
		clarify_doctor = _resolve_target_doctor(clarify_target_role, request.POST.get('clarify_doctor_id'))
		clarify_question = (request.POST.get('clarify_question') or '').strip()
		if request_clarification and clarify_target_role in {
			ClarificationRequest.TARGET_ADMIN,
			ClarificationRequest.TARGET_DOCTOR,
		} and clarify_question and (clarify_target_role != ClarificationRequest.TARGET_DOCTOR or clarify_doctor):
			ClarificationRequest.objects.create(
				asker=request.user,
				post=new_post,
				target_role=clarify_target_role,
				target_doctor=clarify_doctor,
				question=clarify_question,
			)
			messages.success(request, 'Post imewekwa na imetumwa kwa clarification.')
			return redirect('chats:feed_posts')
		if request_clarification and clarify_target_role == ClarificationRequest.TARGET_DOCTOR and not clarify_doctor:
			messages.warning(request, 'Chagua daktari kabla ya kutuma clarification.')
			return redirect('chats:post_create')

		if publish_as_status:
			messages.success(request, 'Post imewekwa kwenye jamii na pia imewekwa kama status.')
		else:
			messages.success(request, 'Post imewekwa kwenye jamii.')
		return redirect('chats:feed_posts')


class ToggleLikeView(LoginRequiredMixin, View):
	def post(self, request, post_id, *args, **kwargs):
		post = get_object_or_404(CommunityPost, pk=post_id)
		liked = False
		if post.likes.filter(pk=request.user.pk).exists():
			post.likes.remove(request.user)
		else:
			post.likes.add(request.user)
			liked = True

		if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
			return JsonResponse(
				{
					'ok': True,
					'post_id': post.id,
					'likes': post.likes.count(),
					'liked': liked,
				}
			)
		return redirect('chats:feed')


class AddCommentView(LoginRequiredMixin, View):
	def post(self, request, post_id, *args, **kwargs):
		post = get_object_or_404(CommunityPost, pk=post_id)
		next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'chats:feed'
		content = (request.POST.get('content') or '').strip()
		is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
		parent_id = request.POST.get('parent_id')
		parent_comment = None
		if parent_id and str(parent_id).isdigit():
			parent_comment = CommunityReply.objects.filter(pk=parent_id, post=post).first()
		if parent_id and parent_comment is None:
			if is_ajax:
				return JsonResponse({'ok': False, 'error': 'Comment unayojibu haipo tena.'}, status=400)
			messages.warning(request, 'Comment unayojibu haipo tena.')
			if next_url.startswith('/'):
				return redirect(next_url)
			return redirect(next_url)
		if content:
			new_comment = CommunityReply.objects.create(post=post, user=request.user, content=content, parent=parent_comment)
			if is_ajax:
				return JsonResponse(
					{
						'ok': True,
						'post_id': post.id,
						'comment_id': new_comment.id,
						'parent_id': parent_comment.id if parent_comment else None,
						'comment_count': post.replies.count(),
						'content': new_comment.content,
						'username': request.user.username,
					}
				)
			messages.success(request, 'Comment imeongezwa.')
		else:
			if is_ajax:
				return JsonResponse({'ok': False, 'error': 'Comment haiwezi kuwa tupu.'}, status=400)
			messages.warning(request, 'Comment haiwezi kuwa tupu.')
		if next_url.startswith('/'):
			return redirect(next_url)
		return redirect(next_url)


class ToggleCommentReactionView(LoginRequiredMixin, View):
	def post(self, request, comment_id, reaction, *args, **kwargs):
		comment = get_object_or_404(CommunityReply, pk=comment_id)
		if reaction == 'like':
			if comment.likes.filter(pk=request.user.pk).exists():
				comment.likes.remove(request.user)
			else:
				comment.likes.add(request.user)
				comment.dislikes.remove(request.user)
		elif reaction == 'dislike':
			if comment.dislikes.filter(pk=request.user.pk).exists():
				comment.dislikes.remove(request.user)
			else:
				comment.dislikes.add(request.user)
				comment.likes.remove(request.user)
		return redirect('chats:feed')


class ReportPostView(LoginRequiredMixin, View):
	def post(self, request, post_id, *args, **kwargs):
		post = get_object_or_404(CommunityPost, pk=post_id)
		form = ContentReportForm(request.POST)
		if form.is_valid():
			ContentReport.objects.create(
				reporter=request.user,
				post=post,
				reason=form.cleaned_data['reason'],
				details=form.cleaned_data['details'],
			)
			if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
				return JsonResponse({'ok': True, 'message': 'Report ya post imetumwa kwa moderator.'})
			messages.success(request, 'Report ya post imetumwa kwa moderator.')
		else:
			if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
				return JsonResponse({'ok': False, 'error': 'Report haijatumwa. Tafadhali jaza sababu.'}, status=400)
			messages.error(request, 'Report haijatumwa. Tafadhali jaza sababu.')
		return redirect('chats:feed')


class ReportCommentView(LoginRequiredMixin, View):
	def post(self, request, comment_id, *args, **kwargs):
		comment = get_object_or_404(CommunityReply, pk=comment_id)
		form = ContentReportForm(request.POST)
		if form.is_valid():
			ContentReport.objects.create(
				reporter=request.user,
				comment=comment,
				reason=form.cleaned_data['reason'],
				details=form.cleaned_data['details'],
			)
			if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
				return JsonResponse({'ok': True, 'message': 'Report ya comment imetumwa kwa moderator.'})
			messages.success(request, 'Report ya comment imetumwa kwa moderator.')
		else:
			if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
				return JsonResponse({'ok': False, 'error': 'Report haijatumwa. Tafadhali jaza sababu.'}, status=400)
			messages.error(request, 'Report haijatumwa. Tafadhali jaza sababu.')
		return redirect('chats:feed')


class DeletePostView(LoginRequiredMixin, View):
    def post(self, request, post_id, *args, **kwargs):
        if not can_moderate(request.user):
            messages.error(request, 'Huna ruhusa ya kufuta post hii.')
            return redirect('chats:feed')
        post = get_object_or_404(CommunityPost, pk=post_id)
        post.delete()
        messages.success(request, 'Post imefutwa.')
        return redirect('chats:feed')


class DeleteCommentView(LoginRequiredMixin, View):
	def post(self, request, comment_id, *args, **kwargs):
		if not can_moderate(request.user):
			messages.error(request, 'Huna ruhusa ya kufuta comment hii.')
			return redirect('chats:feed')
		comment = get_object_or_404(CommunityReply, pk=comment_id)
		comment.delete()
		messages.success(request, 'Comment imefutwa.')
		return redirect('chats:feed')


def _create_group_from_form(request, form):
	audience_gender = _audience_for_user(request.user)
	group = form.save(commit=False)
	group.audience_gender = audience_gender
	group.created_by = request.user
	group.save()
	group.members.add(request.user)

	if form.cleaned_data.get('send_admin_preview'):
		ClarificationRequest.objects.create(
			asker=request.user,
			group=group,
			target_role=ClarificationRequest.TARGET_GROUP_ADMIN,
			question=(form.cleaned_data.get('preview_note') or '').strip() or f'Naomba admin preview ya group: {group.name}',
		)
		messages.success(request, _('Group created. Admin preview request was sent.'))
		return redirect('chats:group_detail', group_id=group.id)

	messages.success(request, _('Group created successfully and you joined automatically.'))
	return redirect('chats:group_detail', group_id=group.id)


class CreateGroupPageView(LoginRequiredMixin, View):
	template_name = 'chats/group_create.html'

	def get(self, request, *args, **kwargs):
		form = CommunityGroupForm()
		context = {
			'group_form': form,
			'audience_gender': _audience_for_user(request.user),
		}
		return render(request, self.template_name, context)

	def post(self, request, *args, **kwargs):
		form = CommunityGroupForm(request.POST, request.FILES)
		if not form.is_valid():
			messages.error(request, _('Group was not created. Please check name and description.'))
			context = {
				'group_form': form,
				'audience_gender': _audience_for_user(request.user),
			}
			return render(request, self.template_name, context, status=400)
		return _create_group_from_form(request, form)


class CreateGroupView(LoginRequiredMixin, View):
	def post(self, request, *args, **kwargs):
		form = CommunityGroupForm(request.POST, request.FILES)
		if not form.is_valid():
			messages.error(request, 'Group haijaundwa. Hakikisha jina na maelezo ni sahihi.')
			return redirect('chats:feed')
		return _create_group_from_form(request, form)


class JoinGroupView(LoginRequiredMixin, View):
	def post(self, request, group_id, *args, **kwargs):
		audience_gender = _audience_for_user(request.user)
		group = get_object_or_404(CommunityGroup, pk=group_id, audience_gender=audience_gender)

		if group.members.filter(pk=request.user.id).exists():
			messages.info(request, f'Tayari uko ndani ya group: {group.name}.')
			return redirect('chats:group_detail', group_id=group.id)

		if group.require_join_approval:
			join_request, created = CommunityGroupJoinRequest.objects.get_or_create(
				group=group,
				user=request.user,
				defaults={
					'status': CommunityGroupJoinRequest.STATUS_PENDING,
					'message': (request.POST.get('message') or '').strip(),
				},
			)
			if not created and join_request.status == CommunityGroupJoinRequest.STATUS_REJECTED:
				join_request.status = CommunityGroupJoinRequest.STATUS_PENDING
				join_request.message = (request.POST.get('message') or '').strip() or join_request.message
				join_request.is_notified = False
				join_request.save(update_fields=['status', 'message', 'is_notified', 'updated_at'])
			messages.success(request, f'Ombi la kujiunga limetumwa kwa admin wa group: {group.name}.')
			return redirect('chats:group_detail', group_id=group.id)

		group.members.add(request.user)
		messages.success(request, f'Umejiunga kwenye group: {group.name}.')
		return redirect('chats:group_detail', group_id=group.id)


class CreateStatusView(LoginRequiredMixin, View):
	def post(self, request, *args, **kwargs):
		next_url = request.POST.get('next') or 'chats:feed_status'
		form = CommunityStatusForm(request.POST, request.FILES)
		if not form.is_valid():
			messages.error(request, 'Status haijatumwa. Angalia urefu wa ujumbe.')
			if isinstance(next_url, str) and next_url.startswith('/'):
				return redirect(next_url)
			return redirect(next_url)

		audience_gender = _audience_for_user(request.user)
		group = None
		group_id = form.cleaned_data.get('group_id')
		if group_id:
			group = CommunityGroup.objects.filter(pk=group_id, audience_gender=audience_gender).first()

		media_files = request.FILES.getlist('media_files')
		if len(media_files) > 8:
			messages.warning(request, 'Unaweza kuongeza media hadi 8 kwa status moja.')
			if isinstance(next_url, str) and next_url.startswith('/'):
				return redirect(next_url)
			return redirect(next_url)

		status_obj = CommunityStatus.objects.create(
			user=request.user,
			group=group,
			audience_gender=audience_gender,
			content=form.cleaned_data['content'],
			image=form.cleaned_data.get('image'),
		)
		for idx, mf in enumerate(media_files):
			content_type = (getattr(mf, 'content_type', '') or '').lower()
			name_l = (getattr(mf, 'name', '') or '').lower()
			is_image = content_type.startswith('image/') or name_l.endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif'))
			is_video = content_type.startswith('video/') or name_l.endswith(('.mp4', '.mov', '.webm', '.mkv', '.avi'))
			if not (is_image or is_video):
				continue
			CommunityStatusMedia.objects.create(
				status=status_obj,
				media_type=CommunityStatusMedia.MEDIA_IMAGE if is_image else CommunityStatusMedia.MEDIA_VIDEO,
				image=mf if is_image else None,
				video=mf if is_video else None,
				sort_order=idx,
			)
		messages.success(request, 'Status imewekwa (itaonekana kwa saa 24).')
		if isinstance(next_url, str) and next_url.startswith('/'):
			return redirect(next_url)
		return redirect(next_url)


class CreateStatusPageView(LoginRequiredMixin, View):
	template_name = 'chats/status_create.html'

	def get(self, request, *args, **kwargs):
		context = _community_post_form_context(request.user, request.GET.get('group'))
		context['status_form'] = CommunityStatusForm(initial={'group_id': context.get('selected_group').id if context.get('selected_group') else None})
		return render(request, self.template_name, context)


class StatusDetailView(LoginRequiredMixin, View):
	template_name = 'chats/status_detail.html'

	def get(self, request, status_id, *args, **kwargs):
		status = get_object_or_404(
			CommunityStatus.objects.select_related('user', 'group').prefetch_related('likes', 'comments__user', 'shares__user', 'media_items'),
			pk=status_id,
			audience_gender=_audience_for_user(request.user),
		)
		status_comments = status.comments.select_related('user').all()
		return render(
			request,
			self.template_name,
			{
				'status': status,
				'status_comments': status_comments,
				'is_liked': status.likes.filter(pk=request.user.id).exists(),
			},
		)


class ToggleStatusLikeView(LoginRequiredMixin, View):
	def post(self, request, status_id, *args, **kwargs):
		status = get_object_or_404(CommunityStatus, pk=status_id, audience_gender=_audience_for_user(request.user))
		if status.likes.filter(pk=request.user.id).exists():
			status.likes.remove(request.user)
		else:
			status.likes.add(request.user)
		messages.success(request, 'Status reaction imehifadhiwa.')
		return redirect('chats:status_detail', status_id=status.id)


class AddStatusCommentView(LoginRequiredMixin, View):
	def post(self, request, status_id, *args, **kwargs):
		status = get_object_or_404(CommunityStatus, pk=status_id, audience_gender=_audience_for_user(request.user))
		content = (request.POST.get('content') or '').strip()
		if not content:
			messages.warning(request, 'Andika comment kwanza.')
			return redirect('chats:status_detail', status_id=status.id)
		CommunityStatusComment.objects.create(status=status, user=request.user, content=content[:400])
		messages.success(request, 'Comment imeongezwa kwenye status.')
		return redirect('chats:status_detail', status_id=status.id)


class ShareStatusView(LoginRequiredMixin, View):
	def post(self, request, status_id, *args, **kwargs):
		status = get_object_or_404(CommunityStatus, pk=status_id, audience_gender=_audience_for_user(request.user))
		CommunityStatusShare.objects.get_or_create(status=status, user=request.user)
		messages.success(request, 'Status imesharewa.')
		return redirect('chats:status_detail', status_id=status.id)


class GroupDetailView(LoginRequiredMixin, View):
	template_name = 'chats/group_detail.html'

	def get(self, request, group_id, *args, **kwargs):
		audience_gender = _audience_for_user(request.user)
		group = get_object_or_404(
			CommunityGroup.objects.select_related('created_by').prefetch_related('members'),
			pk=group_id,
			audience_gender=audience_gender,
		)
		posts_qs = CommunityPost.objects.select_related('user', 'group').prefetch_related('groups', 'likes', 'replies').filter(
			Q(group=group) | Q(groups=group)
		).distinct().order_by('-created_at')
		paginator = Paginator(posts_qs, 8)
		posts_page = paginator.get_page(request.GET.get('page'))
		_prepare_posts_for_feed(posts_page.object_list)

		pending_requests = []
		if group.created_by_id == request.user.id or is_admin(request.user):
			pending_requests = group.join_requests.select_related('user').filter(status=CommunityGroupJoinRequest.STATUS_PENDING)[:30]

		user_request = group.join_requests.filter(user=request.user).first()

		return render(
			request,
			self.template_name,
			{
				'group': group,
				'posts': posts_page,
				'can_moderate': can_moderate(request.user),
				'is_member': group.members.filter(pk=request.user.id).exists(),
				'pending_requests': pending_requests,
				'user_join_request': user_request,
			},
		)


class GroupJoinRequestDecisionView(LoginRequiredMixin, View):
	def post(self, request, request_id, *args, **kwargs):
		join_request = get_object_or_404(CommunityGroupJoinRequest.objects.select_related('group', 'user'), pk=request_id)
		group = join_request.group
		if not (is_admin(request.user) or group.created_by_id == request.user.id):
			messages.error(request, 'Huna ruhusa ya kusimamia maombi ya group hii.')
			return redirect('chats:group_detail', group_id=group.id)

		action = (request.POST.get('action') or '').strip().lower()
		if action == 'approve':
			join_request.status = CommunityGroupJoinRequest.STATUS_APPROVED
			join_request.reviewed_by = request.user
			join_request.is_notified = False
			join_request.save(update_fields=['status', 'reviewed_by', 'is_notified', 'updated_at'])
			group.members.add(join_request.user)
			messages.success(request, f'Umeidhinisha {join_request.user.username} kujiunga.')
		elif action == 'reject':
			join_request.status = CommunityGroupJoinRequest.STATUS_REJECTED
			join_request.reviewed_by = request.user
			join_request.is_notified = True
			join_request.save(update_fields=['status', 'reviewed_by', 'is_notified', 'updated_at'])
			messages.info(request, f'Ombi la {join_request.user.username} limekataliwa.')

		return redirect('chats:group_detail', group_id=group.id)


class ClarificationPostRequestView(LoginRequiredMixin, View):
	def post(self, request, post_id, *args, **kwargs):
		post = get_object_or_404(CommunityPost, pk=post_id)
		form = ClarificationRequestForm(request.POST)
		if form.is_valid():
			target_role = form.cleaned_data['target_role']
			target_group = None
			if target_role == ClarificationRequest.TARGET_GROUP_ADMIN:
				target_group = post.group or post.groups.first()
				if not target_group:
					if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
						return JsonResponse({'ok': False, 'error': 'Post hii haina group ya kutuma preview.'}, status=400)
					messages.error(request, 'Post hii haina group ya kutuma preview.')
					return redirect('chats:feed')
			target_doctor = _resolve_target_doctor(form.cleaned_data['target_role'], form.cleaned_data.get('doctor_id'))
			ClarificationRequest.objects.create(
				asker=request.user,
				post=post,
				group=target_group,
				target_role=target_role,
				target_doctor=target_doctor,
				question=form.cleaned_data['question'],
			)
			if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
				return JsonResponse({'ok': True, 'message': 'Ombi la ufafanuzi limetumwa.'})
			messages.success(request, 'Ombi la ufafanuzi limetumwa.')
		else:
			if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
				return JsonResponse({'ok': False, 'error': 'Ufafanuzi haukutumwa. Jaza swali sahihi.'}, status=400)
			messages.error(request, 'Ufafanuzi haukutumwa. Jaza swali sahihi.')
		return redirect('chats:feed')


class ClarificationCommentRequestView(LoginRequiredMixin, View):
	def post(self, request, comment_id, *args, **kwargs):
		comment = get_object_or_404(CommunityReply, pk=comment_id)
		form = ClarificationRequestForm(request.POST)
		if form.is_valid():
			target_role = form.cleaned_data['target_role']
			target_group = None
			if target_role == ClarificationRequest.TARGET_GROUP_ADMIN:
				target_group = comment.post.group or comment.post.groups.first()
				if not target_group:
					if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
						return JsonResponse({'ok': False, 'error': 'Comment hii haina group ya kutuma preview.'}, status=400)
					messages.error(request, 'Comment hii haina group ya kutuma preview.')
					return redirect('chats:feed')
			target_doctor = _resolve_target_doctor(form.cleaned_data['target_role'], form.cleaned_data.get('doctor_id'))
			ClarificationRequest.objects.create(
				asker=request.user,
				comment=comment,
				group=target_group,
				target_role=target_role,
				target_doctor=target_doctor,
				question=form.cleaned_data['question'],
			)
			if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
				return JsonResponse({'ok': True, 'message': 'Ombi la ufafanuzi wa comment limetumwa.'})
			messages.success(request, 'Ombi la ufafanuzi wa comment limetumwa.')
		else:
			if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
				return JsonResponse({'ok': False, 'error': 'Ufafanuzi haukutumwa. Jaza swali sahihi.'}, status=400)
			messages.error(request, 'Ufafanuzi haukutumwa. Jaza swali sahihi.')
		return redirect('chats:feed')


class ClarificationInboxView(LoginRequiredMixin, View):
	template_name = 'chats/clarification_inbox.html'

	def get(self, request, *args, **kwargs):
		if not (is_admin(request.user) or is_doctor(request.user) or request.user.created_community_groups.exists()):
			messages.error(request, 'Huna ruhusa kuona clarification inbox.')
			return redirect('chats:feed')
		queries = ClarificationRequest.objects.select_related('asker', 'post__user', 'comment__user', 'group', 'responded_by', 'target_doctor', 'asker__ai_persona', 'target_doctor__ai_persona').prefetch_related('messages__user', 'likes', 'dislikes')
		if is_admin(request.user):
			queries = queries.filter(
				Q(target_role=ClarificationRequest.TARGET_ADMIN)
				| Q(target_role=ClarificationRequest.TARGET_GROUP_ADMIN)
			)
		elif is_doctor(request.user):
			queries = queries.filter(target_role=ClarificationRequest.TARGET_DOCTOR).filter(
				Q(target_doctor=request.user) | Q(target_doctor__isnull=True)
			)
		else:
			queries = queries.filter(
				target_role=ClarificationRequest.TARGET_GROUP_ADMIN,
				group__created_by=request.user,
			)
		for clarification in queries:
			_prepare_user_avatar(clarification.asker)
			if clarification.target_doctor:
				_prepare_user_avatar(clarification.target_doctor)
			if clarification.responded_by:
				_prepare_user_avatar(clarification.responded_by)
			clarification.can_user_respond = _can_respond_to_clarification(request.user, clarification)
			clarification.can_user_participate = _can_participate_in_clarification(request.user, clarification)
		return render(request, self.template_name, {'requests': queries})


class ClarificationRespondView(LoginRequiredMixin, View):
	def post(self, request, clarification_id, *args, **kwargs):
		clarification = get_object_or_404(ClarificationRequest, pk=clarification_id)
		next_url = request.POST.get('next') or 'chats:clarification_inbox'
		if not _can_respond_to_clarification(request.user, clarification):
			messages.error(request, 'Huna ruhusa kujibu clarification hii.')
			return redirect(next_url)

		response = (request.POST.get('response') or '').strip()
		if not response:
			messages.warning(request, 'Andika majibu kwanza.')
			return redirect(next_url)

		clarification.response = response
		clarification.status = ClarificationRequest.STATUS_ANSWERED
		clarification.responded_by = request.user
		clarification.save(update_fields=['response', 'status', 'responded_by', 'updated_at'])
		messages.success(request, 'Clarification imejibiwa kikamilifu.')
		return redirect(next_url)


class ClarificationMessageCreateView(LoginRequiredMixin, View):
	def post(self, request, clarification_id, *args, **kwargs):
		clarification = get_object_or_404(ClarificationRequest, pk=clarification_id)
		next_url = request.POST.get('next') or 'chats:clarification_inbox'
		if not _can_participate_in_clarification(request.user, clarification):
			messages.error(request, 'Huna ruhusa kujibu thread hii ya clarification.')
			return redirect(next_url)
		content = (request.POST.get('content') or '').strip()
		if not content:
			messages.warning(request, 'Andika reply kwanza.')
			return redirect(next_url)
		ClarificationMessage.objects.create(
			clarification=clarification,
			user=request.user,
			content=content,
		)
		messages.success(request, 'Reply ya clarification imetumwa.')
		return redirect(next_url)


class ClarificationReactionView(LoginRequiredMixin, View):
	def post(self, request, clarification_id, reaction, *args, **kwargs):
		clarification = get_object_or_404(ClarificationRequest, pk=clarification_id)
		next_url = request.POST.get('next') or 'chats:clarification_inbox'
		if not _can_participate_in_clarification(request.user, clarification):
			messages.error(request, 'Huna ruhusa kureact clarification hii.')
			return redirect(next_url)
		if reaction == 'like':
			if clarification.likes.filter(pk=request.user.pk).exists():
				clarification.likes.remove(request.user)
			else:
				clarification.likes.add(request.user)
				clarification.dislikes.remove(request.user)
		elif reaction == 'dislike':
			if clarification.dislikes.filter(pk=request.user.pk).exists():
				clarification.dislikes.remove(request.user)
			else:
				clarification.dislikes.add(request.user)
				clarification.likes.remove(request.user)
		return redirect(next_url)


class PrivateConversationStartView(LoginRequiredMixin, View):
	template_name = 'chats/start_private_chat.html'

	def get(self, request, doctor_id, *args, **kwargs):
		doctor_user = get_object_or_404(User, pk=doctor_id)
		if not getattr(doctor_user, 'doctor_profile', None) or not doctor_user.doctor_profile.verified:
			messages.error(request, 'Doctor huyu bado hajathibitishwa.')
			return redirect('doctor:hub')
		form = PrivateConversationStartForm()
		return render(request, self.template_name, {'doctor_user': doctor_user, 'form': form})

	def post(self, request, doctor_id, *args, **kwargs):
		doctor_user = get_object_or_404(User, pk=doctor_id)
		form = PrivateConversationStartForm(request.POST)
		if form.is_valid():
			conversation = PrivateConversation.objects.create(
				patient=request.user,
				doctor=doctor_user,
				subject=form.cleaned_data['subject'],
			)
			PrivateMessage.objects.create(
				conversation=conversation,
				sender=request.user,
				content=form.cleaned_data['opening_message'],
			)
			messages.success(request, 'Private chat imeanzishwa na doctor.')
			return redirect('chats:conversation_detail', conversation_id=conversation.id)
		return render(request, self.template_name, {'doctor_user': doctor_user, 'form': form})


class ConversationInboxView(LoginRequiredMixin, View):
	template_name = 'chats/private_inbox.html'

	def get(self, request, *args, **kwargs):
		conversations = PrivateConversation.objects.filter(
			Q(patient=request.user) | Q(doctor=request.user)
		).select_related('patient', 'doctor')
		return render(
			request,
			self.template_name,
			{
				'conversations': conversations,
				'is_doctor_account': is_doctor(request.user),
			},
		)


class ConversationDetailView(LoginRequiredMixin, View):
	template_name = 'chats/private_thread.html'

	def get_conversation(self, request, conversation_id):
		conversation = get_object_or_404(
			PrivateConversation.objects.select_related('patient', 'doctor').prefetch_related('messages__sender'),
			pk=conversation_id,
		)
		if not (is_admin(request.user) or request.user in [conversation.patient, conversation.doctor]):
			raise PermissionError
		return conversation

	def get(self, request, conversation_id, *args, **kwargs):
		try:
			conversation = self.get_conversation(request, conversation_id)
		except PermissionError:
			messages.error(request, 'Huna ruhusa ya kuona conversation hii.')
			return redirect('chats:inbox')

		conversation.messages.exclude(sender=request.user).update(is_read=True)
		doctor_profile_id = getattr(getattr(conversation.doctor, 'doctor_profile', None), 'id', None)
		is_patient_side = request.user == conversation.patient
		return render(
			request,
			self.template_name,
			{
				'conversation': conversation,
				'form': PrivateMessageForm(),
				'doctor_profile_id': doctor_profile_id,
				'is_patient_side': is_patient_side,
			},
		)

	def post(self, request, conversation_id, *args, **kwargs):
		try:
			conversation = self.get_conversation(request, conversation_id)
		except PermissionError:
			messages.error(request, 'Huna ruhusa ya kuandika kwenye conversation hii.')
			return redirect('chats:inbox')

		form = PrivateMessageForm(request.POST, request.FILES)
		if form.is_valid():
			message = PrivateMessage.objects.create(
				conversation=conversation,
				sender=request.user,
				content=form.cleaned_data['content'],
				attachment=form.cleaned_data.get('attachment'),
			)
			if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
				return JsonResponse({'ok': True, 'message': _serialize_private_message(message)})
			messages.success(request, 'Ujumbe umetumwa.')
			return redirect('chats:conversation_detail', conversation_id=conversation.id)
		if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
			return JsonResponse({'ok': False, 'errors': form.errors.get_json_data(), 'error': 'Ujumbe haujatumwa.'}, status=400)
		return render(request, self.template_name, {'conversation': conversation, 'form': form})


class ConversationMessagesPollView(LoginRequiredMixin, View):
	"""Lightweight JSON endpoint — returns messages newer than ?since=<id>.
	Used by the frontend as a reliable real-time fallback / complement to WebSocket."""

	def get(self, request, conversation_id, *args, **kwargs):
		conversation = get_object_or_404(
			PrivateConversation.objects.select_related('patient', 'doctor'),
			pk=conversation_id,
		)
		if not (is_admin(request.user) or request.user in [conversation.patient, conversation.doctor]):
			return JsonResponse({'ok': False, 'error': 'No permission'}, status=403)

		try:
			since_id = int(request.GET.get('since', 0) or 0)
		except (ValueError, TypeError):
			since_id = 0

		qs = PrivateMessage.objects.filter(
			conversation=conversation,
			id__gt=since_id,
		).select_related('sender').order_by('id')

		# mark incoming messages read
		qs.exclude(sender=request.user).update(is_read=True)

		data = []
		for msg in qs:
			data.append(_serialize_private_message(msg))

		call_events = _pop_private_call_events(request.user.id, conversation.id)

		return JsonResponse({'ok': True, 'messages': data, 'call_events': call_events})


@method_decorator(csrf_exempt, name='dispatch')
class ConversationCallSignalView(LoginRequiredMixin, View):
	"""HTTP fallback for call control signaling.
	Helps incoming call alerts appear even if websocket delivery is temporarily unavailable."""

	def post(self, request, conversation_id, *args, **kwargs):
		conversation = get_object_or_404(
			PrivateConversation.objects.select_related('patient', 'doctor'),
			pk=conversation_id,
		)
		if not (is_admin(request.user) or request.user in [conversation.patient, conversation.doctor]):
			return JsonResponse({'ok': False, 'error': 'No permission'}, status=403)

		try:
			payload = json.loads(request.body.decode('utf-8') or '{}')
		except (json.JSONDecodeError, UnicodeDecodeError):
			payload = {}

		event = str(payload.get('event') or '').strip()
		if event not in CALL_SIGNAL_EVENTS:
			return JsonResponse({'ok': False, 'error': 'Invalid call event'}, status=400)

		call_id = str(payload.get('call_id') or '').strip()[:80]
		if not call_id:
			return JsonResponse({'ok': False, 'error': 'Missing call_id'}, status=400)

		call_mode = str(payload.get('call_mode') or 'audio').strip().lower()
		if call_mode not in {'audio', 'video'}:
			call_mode = 'audio'

		recipient_id = conversation.doctor_id if request.user.id == conversation.patient_id else conversation.patient_id
		event_payload = {
			'event': event,
			'call_id': call_id,
			'call_mode': call_mode,
			'conversation_id': conversation.id,
			'sender_id': request.user.id,
			'sender_name': request.user.get_full_name() or request.user.username,
		}

		reason = str(payload.get('reason') or '').strip()
		if reason:
			event_payload['reason'] = reason[:160]

		_queue_private_call_event(recipient_id, conversation.id, event_payload)
		return JsonResponse({'ok': True})


class ConversationCallInboxView(LoginRequiredMixin, View):
	"""Global call events for the current user, usable from any page."""

	def get(self, request, *args, **kwargs):
		events = _pop_global_private_call_events(request.user.id)
		return JsonResponse({'ok': True, 'events': events})


class DeletePrivateMessageView(LoginRequiredMixin, View):
	"""Delete a private message (sender only, or admin)."""

	def post(self, request, conversation_id, message_id, *args, **kwargs):
		conversation = get_object_or_404(PrivateConversation, pk=conversation_id)
		if not (is_admin(request.user) or request.user in [conversation.patient, conversation.doctor]):
			return JsonResponse({'ok': False, 'error': 'No permission'}, status=403)

		message = get_object_or_404(PrivateMessage, pk=message_id, conversation=conversation)
		if not (is_admin(request.user) or message.sender_id == request.user.id):
			return JsonResponse({'ok': False, 'error': 'Only sender can delete this message'}, status=403)

		message.delete()
		return JsonResponse({'ok': True, 'message_id': message_id})


class ModeratorDashboardView(ModeratorRequiredMixin, View):
	template_name = 'chats/moderator_dashboard.html'

	def get(self, request, *args, **kwargs):
		reports = ContentReport.objects.select_related('reporter', 'post__user', 'comment__user').order_by('-created_at')
		posts = CommunityPost.objects.select_related('user').order_by('-created_at')[:10]
		comments = CommunityReply.objects.select_related('user', 'post').order_by('-created_at')[:10]
		return render(
			request,
			self.template_name,
			{
				'reports': reports,
				'posts': posts,
				'comments': comments,
			},
		)


class ResolveReportView(ModeratorRequiredMixin, View):
	def post(self, request, report_id, *args, **kwargs):
		report = get_object_or_404(ContentReport, pk=report_id)
		report.status = request.POST.get('status', ContentReport.STATUS_RESOLVED)
		report.reviewed_by = request.user
		report.save(update_fields=['status', 'reviewed_by'])
		messages.success(request, 'Report imeboreshwa status.')
		return redirect('chats:moderator_dashboard')
