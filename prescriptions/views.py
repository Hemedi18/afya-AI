from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import Http404
from .models import Prescription
from pharmacy.models import PharmacyStaff

@login_required
def prescription_list(request):
	prescriptions = Prescription.objects.filter(user=request.user)
	return render(request, 'prescriptions/prescription_list.html', {'prescriptions': prescriptions})

@login_required
def prescription_upload(request):
	# Placeholder for upload logic
	return render(request, 'prescriptions/prescription_upload.html')

@login_required
def prescription_detail(request, pk):
    prescription = get_object_or_404(Prescription, pk=pk)
    # Access allowed for the patient or pharmacy staff/owners associated with the order
    is_owner = prescription.user == request.user
    is_staff = PharmacyStaff.objects.filter(user=request.user).exists() or \
               (prescription.order and prescription.order.suborders.filter(pharmacy__owner=request.user).exists())
    
    if not (is_owner or is_staff):
        raise Http404("Access denied.")
        
    return render(request, 'prescriptions/prescription_detail.html', {
        'prescription': prescription,
        'is_staff': is_staff
    })

@login_required
def verify_prescription(request, pk):
    """Handles approval or rejection of prescriptions from the staff portal."""
    prescription = get_object_or_404(Prescription, pk=pk)
    if request.method == 'POST':
        status = request.POST.get('status')
        notes = request.POST.get('notes', '')
        
        # Ensure the user is a PharmacyStaff to be recorded as 'verified_by'
        staff_member = PharmacyStaff.objects.filter(user=request.user).first()

        if status in ['approved', 'rejected']:
            prescription.status = status
            prescription.notes = notes
            prescription.verified_by = staff_member
            prescription.save()
            messages.success(request, f"Prescription status updated to {status}.")
    return redirect('pharmacy:staff_dashboard')

# Create your views here.
