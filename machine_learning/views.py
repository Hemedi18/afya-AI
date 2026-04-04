import json as _json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from card.models import HealthCard
from card.views import _build_selected_health_data
from .face_service import (
    build_face_embedding,
    build_face_embedding_from_b64,
    check_frame_quality,
    check_liveness_multiframe,
    cosine_similarity,
    find_best_match,
)
from .models import FaceEnrollment, FaceScanAudit


FACE_MATCH_THRESHOLD = 0.78
LOOKUP_MATCH_THRESHOLD = 0.72
ENROLL_DUPLICATE_THRESHOLD = 0.88
CARD_FACE_SESSION_SECONDS = 60 * 20


def _is_verified_doctor_or_admin(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    doctor_profile = getattr(user, 'doctor_profile', None)
    return bool(doctor_profile and getattr(doctor_profile, 'verified', False))


def _best_lookup_match(embeddings, candidates):
    """
    Robust lookup: compare every captured frame embedding with each enrolled user embedding.
    Score per user = max cosine over all frames.
    """
    best_user_id = None
    best_score = -1.0
    for user_id, enrolled_emb in candidates:
        score = max(cosine_similarity(frame_emb, enrolled_emb) for frame_emb in embeddings)
        if score > best_score:
            best_score = score
            best_user_id = user_id
    return best_user_id, max(0.0, best_score)


def _find_duplicate_face_user(embedding, current_user_id):
    """Return (user_id, score) if this face is already enrolled by another user."""
    best_user_id = None
    best_score = -1.0
    qs = FaceEnrollment.objects.filter(active=True).exclude(embedding=[]).exclude(user_id=current_user_id)
    for enr in qs:
        score = cosine_similarity(embedding, enr.embedding)
        if score > best_score:
            best_score = score
            best_user_id = enr.user_id

    if best_user_id is not None and best_score >= ENROLL_DUPLICATE_THRESHOLD:
        return best_user_id, best_score
    return None, max(0.0, best_score)


@login_required
def face_privacy_docs(request):
    return render(request, 'machine_learning/face_docs.html')


@login_required
def enroll_face(request):
    if request.method != 'POST':
        return redirect('card:details')

    image_file = request.FILES.get('face_image')
    if not image_file:
        messages.error(request, 'Tafadhali chagua picha ya uso.')
        return redirect(request.POST.get('next') or 'card:details')

    try:
        embedding = build_face_embedding(image_file)
    except Exception:
        messages.error(request, 'Imeshindikana kusoma picha. Tumia picha iliyo wazi ya uso.')
        return redirect(request.POST.get('next') or 'card:details')

    duplicate_user_id, duplicate_score = _find_duplicate_face_user(embedding, request.user.id)
    if duplicate_user_id is not None:
        messages.error(
            request,
            f'Face hii imefanana na user mwingine aliyesajiliwa tayari (confidence {duplicate_score:.0%}). '
            'Tumia uso wa mmiliki halisi wa akaunti hii.',
        )
        return redirect(request.POST.get('next') or 'card:details')

    image_file.seek(0)
    enrollment, _ = FaceEnrollment.objects.get_or_create(user=request.user)
    enrollment.reference_image = image_file
    enrollment.embedding = embedding
    enrollment.embedding_version = 'v1'
    enrollment.active = True
    enrollment.last_verified_at = timezone.now()
    enrollment.save()

    request.session['card_face_verified_until'] = int(timezone.now().timestamp()) + CARD_FACE_SESSION_SECONDS
    messages.success(request, 'Face enrollment imehifadhiwa. Card features zimefunguliwa.')
    return redirect(request.POST.get('next') or 'card:details')


@login_required
def verify_face_for_card(request):
    if request.method != 'POST':
        return redirect('card:details')

    next_url = request.POST.get('next') or reverse('card:home')
    image_file = request.FILES.get('face_probe')
    if not image_file:
        messages.error(request, 'Weka picha ya uso kuthibitisha card access.')
        return redirect(next_url)

    enrollment = FaceEnrollment.objects.filter(user=request.user, active=True).first()
    if not enrollment or not enrollment.embedding:
        messages.warning(request, 'Hujaweka face enrollment bado. Tafadhali enroll uso wako kwanza.')
        return redirect('card:details')

    try:
        probe = build_face_embedding(image_file)
    except Exception:
        messages.error(request, 'Picha haijasomeka vizuri. Jaribu tena na picha iliyo wazi ya uso.')
        return redirect(next_url)

    score = cosine_similarity(probe, enrollment.embedding)
    ok = score >= FACE_MATCH_THRESHOLD

    FaceScanAudit.objects.create(
        scanner=request.user,
        matched_user=request.user if ok else None,
        purpose=FaceScanAudit.PURPOSE_CARD_ACCESS,
        similarity=score,
        success=ok,
        notes='card access verification',
    )

    if not ok:
        messages.error(request, f'Face verification haijafanikiwa (confidence {score:.2f}). Jaribu tena.')
        return redirect(next_url)

    enrollment.last_verified_at = timezone.now()
    enrollment.save(update_fields=['last_verified_at', 'updated_at'])
    request.session['card_face_verified_until'] = int(timezone.now().timestamp()) + CARD_FACE_SESSION_SECONDS
    messages.success(request, 'Face verification imefanikiwa. Unaweza kutumia card features.')
    return redirect(next_url)


@login_required
def admin_doctor_face_scan(request):
    if not _is_verified_doctor_or_admin(request.user):
        messages.error(request, 'Huna ruhusa ya kutumia face scan lookup.')
        return redirect('main:home')

    matched_payload = None
    matched_payload_pretty = None
    matched_card = None
    similarity = None

    matched_user_id = request.GET.get('matched_user_id')
    if matched_user_id:
        user = User.objects.filter(id=matched_user_id).first()
        matched_card = HealthCard.objects.filter(user=user).first() if user else None
        if matched_card:
            matched_payload = _build_selected_health_data(matched_card)
            matched_payload_pretty = _json.dumps(matched_payload, indent=2, ensure_ascii=False)
        if request.GET.get('similarity'):
            try:
                similarity = float(request.GET.get('similarity'))
            except Exception:
                similarity = None

    if request.method == 'POST':
        image_file = request.FILES.get('face_probe')
        if not image_file:
            messages.error(request, 'Weka picha ya uso kuscan.')
        else:
            try:
                probe = build_face_embedding(image_file)
            except Exception:
                messages.error(request, 'Picha haijasomeka. Tumia picha iliyo wazi ya uso.')
            else:
                candidates = []
                for enr in FaceEnrollment.objects.filter(active=True).exclude(embedding=[]):
                    candidates.append((enr.user_id, enr.embedding))

                best_user_id, best_score = find_best_match(probe, candidates)
                similarity = best_score

                if best_user_id is None or best_score < LOOKUP_MATCH_THRESHOLD:
                    FaceScanAudit.objects.create(
                        scanner=request.user,
                        purpose=FaceScanAudit.PURPOSE_ADMIN_LOOKUP,
                        similarity=best_score or 0.0,
                        success=False,
                        notes='No reliable face match',
                    )
                    messages.warning(request, f'Hakuna match ya kuaminika imepatikana (confidence {best_score:.2f}).')
                else:
                    user = User.objects.filter(id=best_user_id).first()
                    matched_card = HealthCard.objects.filter(user=user).first() if user else None
                    if matched_card:
                        matched_payload = _build_selected_health_data(matched_card)
                        matched_payload_pretty = _json.dumps(matched_payload, indent=2, ensure_ascii=False)
                        request.session[f'card_access_{matched_card.public_token}'] = True
                    FaceScanAudit.objects.create(
                        scanner=request.user,
                        matched_user=user,
                        purpose=FaceScanAudit.PURPOSE_ADMIN_LOOKUP,
                        similarity=best_score,
                        success=bool(matched_card),
                        notes='Matched via face scan lookup',
                    )
                    if matched_card:
                        messages.success(request, f'Face match imepatikana (confidence {best_score:.2f}).')
                    else:
                        messages.warning(request, 'Face match imepatikana lakini user hana card data.')

    return render(request, 'machine_learning/face_scan_lookup.html', {
        'matched_payload': matched_payload,
        'matched_payload_pretty': matched_payload_pretty,
        'matched_card': matched_card,
        'similarity': similarity,
        'threshold': FACE_MATCH_THRESHOLD,
    })


# ─── Live Face Scan ───────────────────────────────────────────────────────────

_LIVENESS_ERROR_MSGS = {
    'static_image':      'Mfumo uliona fremu zimetulia sana. Ikiwa uko live, sogeza kichwa kidogo au kope mara chache kisha jaribu tena.',
    'not_enough_frames': 'Picha haitoshi. Simama bila kusogea.',
    'unstable':          'Harakati nyingi mno. Simama bado kidogo kabla ya scan.',
    'image_too_small':   'Picha ni ndogo sana.',
    'too_dark':          'Giza sana. Tafadhali ongeza mwanga.',
    'too_bright':        'Mwanga mkali sana. Punguza mwanga au usimame mbali na chanzo cha mwanga.',
    'poor_quality':      'Picha haiko wazi au haina maudhui ya kutosha.',
    'bad_image':         'Imeshindikana kusoma picha. Jaribu tena.',
}


@login_required
def live_face_scan(request):
    """
    GET  → renders the live camera scan page.
    POST → JSON API: receives base64 frames, performs liveness + enroll/verify.
    """
    enrollment = FaceEnrollment.objects.filter(user=request.user, active=True).first()
    has_enrollment = bool(enrollment and enrollment.embedding)

    if request.method == 'GET':
        next_url = request.GET.get('next') or reverse('card:home')
        purpose = 'enroll' if not has_enrollment else request.GET.get('purpose', 'verify')
        return render(request, 'machine_learning/face_scan_live.html', {
            'next_url': next_url,
            'purpose': purpose,
            'has_enrollment': has_enrollment,
        })

    # ── POST (JSON) ───────────────────────────────────────────────────────────
    try:
        data = _json.loads(request.body)
    except Exception:
        return JsonResponse({'ok': False, 'error': 'invalid_request', 'message': 'Ombi si sahihi.'}, status=400)

    frames_b64 = data.get('frames', [])
    purpose    = (data.get('purpose', 'verify') or 'verify').strip().lower()
    next_url   = data.get('next') or reverse('card:home')

    if len(frames_b64) < 2:
        return JsonResponse({'ok': False, 'error': 'not_enough_frames',
                             'message': 'Picha haitoshi. Simama bila kusogea.'})

    # Quality check on first frame
    q_ok, q_reason = check_frame_quality(frames_b64[0])
    if not q_ok:
        return JsonResponse({'ok': False, 'error': q_reason,
                             'message': _LIVENESS_ERROR_MSGS.get(q_reason, 'Ubora wa picha si nzuri.')})

    # Build embeddings
    try:
        embeddings = [build_face_embedding_from_b64(f) for f in frames_b64]
    except Exception:
        return JsonResponse({'ok': False, 'error': 'embedding_failed',
                             'message': 'Imeshindikana kusoma picha. Jaribu tena.'})

    # Liveness check REMOVED: allow static images for all purposes (enroll, lookup, verify)
    # live_ok, live_reason = check_liveness_multiframe(embeddings)
    # if purpose in {'enroll', 'lookup'} and not live_ok:
    #     return JsonResponse({'ok': False, 'error': live_reason,
    #                          'message': _LIVENESS_ERROR_MSGS.get(live_reason, 'Uthibitisho wa uhalisi umeshindwa.')})

    best_embedding = embeddings[len(embeddings) // 2]  # middle frame is usually sharpest

    # ── ADMIN/DOCTOR LOOKUP ──────────────────────────────────────────────────
    if purpose == 'lookup':
        if not _is_verified_doctor_or_admin(request.user):
            return JsonResponse({
                'ok': False,
                'error': 'forbidden',
                'message': 'Huna ruhusa ya kufanya face lookup.',
            }, status=403)

        candidates = []
        for enr in FaceEnrollment.objects.filter(active=True).exclude(embedding=[]):
            candidates.append((enr.user_id, enr.embedding))

        best_user_id, best_score = _best_lookup_match(embeddings, candidates)

        if best_user_id is None or best_score < LOOKUP_MATCH_THRESHOLD:
            FaceScanAudit.objects.create(
                scanner=request.user,
                purpose=FaceScanAudit.PURPOSE_ADMIN_LOOKUP,
                similarity=best_score or 0.0,
                success=False,
                notes='live lookup: no reliable face match',
            )
            return JsonResponse({
                'ok': False,
                'error': 'match_failed',
                'message': f'Hakuna match ya kuaminika imepatikana (confidence {best_score:.0%}).',
            })

        user = User.objects.filter(id=best_user_id).first()
        matched_card = HealthCard.objects.filter(user=user).first() if user else None
        FaceScanAudit.objects.create(
            scanner=request.user,
            matched_user=user,
            purpose=FaceScanAudit.PURPOSE_ADMIN_LOOKUP,
            similarity=best_score,
            success=bool(matched_card),
            notes='live lookup: face matched',
        )

        if not matched_card:
            return JsonResponse({
                'ok': False,
                'error': 'no_card',
                'message': 'Face match imepatikana lakini user hana card data.',
            })

        # Open exact same page style as QR scanned card information.
        request.session[f'card_access_{matched_card.public_token}'] = True
        lookup_next = reverse('card:public_profile', kwargs={'token': matched_card.public_token})
        return JsonResponse({
            'ok': True,
            'action': 'lookup',
            'next': lookup_next,
            'message': f'Face match imepatikana kwa @{user.username} (confidence {best_score:.0%}).',
        })

    # ── ENROLL ────────────────────────────────────────────────────────────────
    if purpose == 'enroll':
        duplicate_user_id, duplicate_score = _find_duplicate_face_user(best_embedding, request.user.id)
        if duplicate_user_id is not None:
            return JsonResponse({
                'ok': False,
                'error': 'duplicate_face',
                'message': (
                    f'Face hii imefanana na user mwingine aliyesajiliwa tayari (confidence {duplicate_score:.0%}). '
                    'Tumia uso wa mmiliki halisi wa akaunti hii.'
                ),
            })

        enr, _ = FaceEnrollment.objects.get_or_create(user=request.user)
        enr.embedding         = best_embedding
        enr.embedding_version = 'v1-live'
        enr.active            = True
        enr.last_verified_at  = timezone.now()
        enr.save()

        request.session['card_face_verified_until'] = (
            int(timezone.now().timestamp()) + CARD_FACE_SESSION_SECONDS
        )
        FaceScanAudit.objects.create(
            scanner=request.user, matched_user=request.user,
            purpose=FaceScanAudit.PURPOSE_CARD_ACCESS,
            similarity=1.0, success=True, notes='live-camera enrollment',
        )
        return JsonResponse({
            'ok': True, 'action': 'enrolled', 'next': next_url,
            'message': '✅ Uso umehifadhiwa! Card features zimefunguliwa.',
        })

    # ── VERIFY ────────────────────────────────────────────────────────────────
    if not has_enrollment:
        enroll_url = (
            reverse('machine_learning:live_face_scan') + '?purpose=enroll&next=' + next_url
        )
        return JsonResponse({
            'ok': False, 'error': 'no_enrollment', 'suggest_enroll': True,
            'next_enroll': enroll_url,
            'message': 'Hujawahi hifadhi uso wako. Kwanza enroll uso wako.',
        })

    score = cosine_similarity(best_embedding, enrollment.embedding)
    ok    = score >= FACE_MATCH_THRESHOLD

    FaceScanAudit.objects.create(
        scanner=request.user, matched_user=request.user if ok else None,
        purpose=FaceScanAudit.PURPOSE_CARD_ACCESS,
        similarity=score, success=ok, notes='live-camera verification',
    )

    if ok:
        enrollment.last_verified_at = timezone.now()
        enrollment.save(update_fields=['last_verified_at', 'updated_at'])
        request.session['card_face_verified_until'] = (
            int(timezone.now().timestamp()) + CARD_FACE_SESSION_SECONDS
        )
        return JsonResponse({
            'ok': True, 'action': 'verified', 'next': next_url,
            'message': f'✅ Uthibitisho umefanikiwa! (Confidence: {score:.0%})',
        })

    return JsonResponse({
        'ok': False, 'error': 'match_failed',
        'message': (
            f'Uso haujatambuliwa (confidence {score:.0%}). '
            'Jaribu tena au enroll upya kama muonekano wako umebadilika.'
        ),
    })
