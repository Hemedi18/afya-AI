from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Child, GrowthRecord, DevelopmentMilestone, ChildMilestone, NutritionTip, Vaccination, ChildVaccination
from .forms import ChildForm, GrowthRecordForm, ChildMilestoneForm, ChildVaccinationForm
from .services import analyze_growth, get_nutrition_tips
from .utils import age_in_months, growth_chart_data
from django.http import JsonResponse

@login_required
def dashboard(request):
	children = Child.objects.filter(user=request.user)
	selected_child = children.first() if children.exists() else None
	growth_info = analyze_growth(selected_child) if selected_child else None
	nutrition_tips = get_nutrition_tips(age_in_months(selected_child.birth_date)) if selected_child else []
	return render(request, "child_growth/dashboard.html", {
		"children": children,
		"selected_child": selected_child,
		"growth_info": growth_info,
		"nutrition_tips": nutrition_tips,
	})

@login_required
def add_child(request):
	if request.method == "POST":
		form = ChildForm(request.POST)
		if form.is_valid():
			child = form.save(commit=False)
			child.user = request.user
			child.save()
			messages.success(request, "Child profile added successfully.")
			return redirect("child_growth:dashboard")
	else:
		form = ChildForm()
	return render(request, "child_growth/add_child.html", {"form": form})

@login_required
def child_detail(request, pk):
	child = get_object_or_404(Child, pk=pk, user=request.user)
	growth_records = child.growth_records.order_by("recorded_at")
	growth_info = analyze_growth(child, growth_records)
	chart_data = growth_chart_data(growth_records)
	milestones = ChildMilestone.objects.filter(child=child)
	vaccinations = ChildVaccination.objects.filter(child=child)
	return render(request, "child_growth/child_detail.html", {
		"child": child,
		"growth_records": growth_records,
		"growth_info": growth_info,
		"chart_data": chart_data,
		"milestones": milestones,
		"vaccinations": vaccinations,
	})

@login_required
def growth_chart(request, child_id):
	child = get_object_or_404(Child, pk=child_id, user=request.user)
	records = child.growth_records.order_by("recorded_at")
	data = growth_chart_data(records)
	return JsonResponse(data)

@login_required
def milestones(request, child_id):
	child = get_object_or_404(Child, pk=child_id, user=request.user)
	milestones = ChildMilestone.objects.filter(child=child)
	all_milestones = DevelopmentMilestone.objects.all()
	if request.method == "POST":
		form = ChildMilestoneForm(request.POST)
		if form.is_valid():
			milestone = form.save(commit=False)
			milestone.child = child
			milestone.save()
			messages.success(request, "Milestone updated.")
			return redirect("child_growth:milestones", child_id=child.id)
	else:
		form = ChildMilestoneForm()
	return render(request, "child_growth/milestones.html", {
		"child": child,
		"milestones": milestones,
		"all_milestones": all_milestones,
		"form": form,
	})
