


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import PubertyProfile, PubertyGuide, PubertyTip, PubertyQuestion, PubertyAnswer
from .forms import PubertyProfileForm, PubertyAssessmentForm, PubertyChatForm
from .services import ai_puberty_response, assess_puberty_stage, recommend_hygiene_products

@login_required
def dashboard(request):
	profile, created = PubertyProfile.objects.get_or_create(
		user=request.user,
		defaults={
			'gender': 'other',
			'age': 13,
			'puberty_stage': 'Not set',
			'concerns': {},
			'country': '',
		}
	)
	tips = PubertyTip.objects.all()[:5]
	guides = PubertyGuide.objects.all()[:4]
	return render(request, "puberty/dashboard.html", {
		"profile": profile,
		"tips": tips,
		"guides": guides,
	})

@login_required
def assessment(request):
	profile, _ = PubertyProfile.objects.get_or_create(user=request.user)
	if request.method == "POST":
		form = PubertyAssessmentForm(request.POST)
		if form.is_valid():
			data = form.cleaned_data
			stage = assess_puberty_stage(data["age"], data["gender"], data["changes_noticed"], data["mood"], data["physical_changes"])
			profile.gender = data["gender"]
			profile.age = data["age"]
			profile.puberty_stage = stage
			profile.concerns = {"changes": data["changes_noticed"], "mood": data["mood"], "physical": data["physical_changes"]}
			profile.save()
			messages.success(request, f"Assessment complete! Your puberty stage: {stage}")
			return redirect("puberty:dashboard")
	else:
		form = PubertyAssessmentForm(initial={"age": profile.age, "gender": profile.gender})
	return render(request, "puberty/assessment.html", {"form": form, "profile": profile})

@login_required
def chat(request):
	profile, _ = PubertyProfile.objects.get_or_create(user=request.user)
	answer = None
	if request.method == "POST":
		form = PubertyChatForm(request.POST)
		if form.is_valid():
			question = form.cleaned_data["question"]
			answer = ai_puberty_response(question, user=request.user)
	else:
		form = PubertyChatForm()
	return render(request, "puberty/chat.html", {"form": form, "answer": answer, "profile": profile})

@login_required
def guides(request):
	profile, _ = PubertyProfile.objects.get_or_create(user=request.user)
	guides = PubertyGuide.objects.all()
	return render(request, "puberty/guides.html", {"guides": guides, "profile": profile})

@login_required
def guide_detail(request, guide_id):
	profile, _ = PubertyProfile.objects.get_or_create(user=request.user)
	guide = get_object_or_404(PubertyGuide, id=guide_id)
	return render(request, "puberty/guide.html", {"guide": guide, "profile": profile})

@login_required
def profile(request):
	profile, _ = PubertyProfile.objects.get_or_create(user=request.user)
	if request.method == "POST":
		form = PubertyProfileForm(request.POST, instance=profile)
		if form.is_valid():
			form.save()
			messages.success(request, "Profile updated successfully.")
			return redirect("puberty:profile")
	else:
		form = PubertyProfileForm(instance=profile)
	hygiene_products = recommend_hygiene_products(profile.gender) if profile.gender else []
	return render(request, "puberty/profile.html", {"form": form, "profile": profile, "hygiene_products": hygiene_products})
