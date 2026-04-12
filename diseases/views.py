import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Avg, Count
from django.utils import timezone
from .models import Disease, UserDisease, DiseaseLog, DiseaseMedication, MedicationLog
from AI_brain.services import generate_ai_text, get_disease_info_from_external_apis
from datetime import timedelta

class DiseaseDashboardView(LoginRequiredMixin, View):
    template_name = 'diseases/user_dashboard.html'

    def get(self, request):
        user_diseases = UserDisease.objects.filter(user=request.user).select_related('disease_ref')
        recent_logs = DiseaseLog.objects.filter(user_disease__user=request.user)[:5]
        
        # Stats for Metrics
        active_count = user_diseases.filter(status='active').count()
        avg_risk = user_diseases.aggregate(Avg('risk_score'))['risk_score__avg'] or 0
        
        # Medication Adherence Logic (Last 7 Days)
        seven_days_ago = timezone.now().date() - timedelta(days=7)
        total_meds = DiseaseMedication.objects.filter(user_disease__user=request.user, is_active=True).count()
        expected_intakes = total_meds * 7
        actual_intakes = MedicationLog.objects.filter(
            medication__user_disease__user=request.user, 
            date__gte=seven_days_ago, 
            taken=True
        ).count()
        adherence_pct = int((actual_intakes / expected_intakes) * 100) if expected_intakes > 0 else 100

        # Prepare Chart Data (Last 7 Logs)
        chart_logs = DiseaseLog.objects.filter(
            user_disease__user=request.user
        ).order_by('date')[:7]
        
        chart_data = {
            'labels': [log.date.strftime('%d %b') for log in chart_logs],
            'severity': [log.severity_score for log in chart_logs],
            'temp': [log.temperature or 0 for log in chart_logs]
        }

        # Quick AI Tip Placeholder (Contextual)
        tip_prompt = f"Toa ushauri mmoja mfupi wa afya kwa Kiswahili kwa mtu mwenye magonjwa haya: {[d.custom_name for d in user_diseases[:2]]}"
        daily_tip = generate_ai_text(tip_prompt, "Kunywa maji ya kutosha na pumzika vizuri leo.")
        
        return render(request, self.template_name, {
            'user_diseases': user_diseases,
            'recent_logs': recent_logs,
            'active_count': active_count,
            'avg_risk': int(avg_risk),
            'adherence_pct': adherence_pct,
            'high_risk_detected': avg_risk > 75,
            'chart_data_json': json.dumps(chart_data),
            'daily_tip': daily_tip,
            'myth_busting_cards': [
                {
                    'title': 'Myth: Magonjwa yote ya kurithi hayana tiba',
                    'fact': 'Fact: Magonjwa mengi ya kurithi yanaweza kudhibitiwa vizuri kwa mtindo wa maisha na tiba sahihi.',
                },
                {
                    'title': 'Myth: Pressure inapanda tu kwa wazee',
                    'fact': 'Fact: Pressure inaweza kumpata mtu wa umri wowote kutokana na stress na lishe.',
                },
            ]
        })

class DiseaseSearchView(LoginRequiredMixin, View):
    def get(self, request):
        query = request.GET.get('q', '').strip()
        if query:
            results = Disease.objects.filter(
                Q(name__icontains=query) | 
                Q(symptoms__icontains=query) |
                Q(body_system__icontains=query)
            )[:10]
        else:
            results = Disease.objects.all()[:20]
        
        return render(request, 'diseases/search_results.html', {
            'results': results,
            'query': query
        })

class AddUserDiseaseView(LoginRequiredMixin, View):
    def post(self, request, disease_id=None):
        disease = get_object_or_404(Disease, id=disease_id) if disease_id else None
        
        UserDisease.objects.create(
            user=request.user,
            disease_ref=disease,
            custom_name=disease.name if disease else request.POST.get('custom_name'),
            status='active',
            is_chronic=disease.is_chronic if disease else False
        )
        messages.success(request, "Ugonjwa umeongezwa kwenye profile yako.")
        return redirect('diseases:user_dashboard')

class LogDiseaseMetricsView(LoginRequiredMixin, View):
    def post(self, request, user_disease_id):
        ud = get_object_or_404(UserDisease, id=user_disease_id, user=request.user)
        
        # Extract metrics
        temp = float(request.POST.get('temperature', 0) or 0)
        sys = int(request.POST.get('bp_systolic', 0) or 0)
        oxy = int(request.POST.get('oxygen_level', 0) or 0)
        
        log, created = DiseaseLog.objects.update_or_create(
            user_disease=ud,
            date=timezone.now().date(),
            defaults={
                'symptoms_noted': request.POST.get('symptoms'),
                'temperature': temp if temp > 0 else None,
                'bp_systolic': sys if sys > 0 else None,
                'oxygen_level': oxy if oxy > 0 else None,
                'severity_score': int(request.POST.get('severity', 1)),
            }
        )

        # Emergency Detection Logic
        alerts = []
        if temp > 39.5: alerts.append("Homa kali sana (Emergency level).")
        if sys > 170: alerts.append("Pressure ya juu sana (Danger).")
        if oxy > 0 and oxy < 92: alerts.append("Kiwango cha oxygen kiko chini.")

        if alerts:
            for alert in alerts:
                messages.error(request, f"🚨 TAHADHARI: {alert} Tafadhali wasiliana na daktari.")
        else:
            messages.success(request, "Log ya leo imehifadhiwa.")

        # Trigger AI Insight after logging
        self._update_ai_insights(ud)
        
        return redirect('diseases:user_dashboard')

    def _update_ai_insights(self, user_disease):
        logs = user_disease.logs.all()[:7]
        if not logs: return

        prompt = (
            f"Analyze logs for {user_disease.custom_name}. "
            f"Recent symptoms: {[l.symptoms_noted for l in logs]}. "
            "Summarize health trend in Swahili. Is user improving or worsening? "
            "Provide 1 specific advice."
        )
        insight = generate_ai_text(prompt, "AI insight haijapatikana.")
        user_disease.last_ai_insight = insight
        
        # Simple heuristic risk scoring
        avg_severity = sum(l.severity_score for l in logs) / len(logs)
        user_disease.risk_score = int(avg_severity * 10)
        user_disease.save()

class DiseaseTimelineView(LoginRequiredMixin, View):
    def get(self, request, user_disease_id):
        ud = get_object_or_404(UserDisease, id=user_disease_id, user=request.user)
        logs = ud.logs.all().order_by('date')
        return render(request, 'diseases/timeline.html', {'ud': ud, 'logs': logs})


class DiseaseWikiSearchView(LoginRequiredMixin, View):
    """
    Handles searching for diseases using external APIs (WHO, Wikipedia)
    and AI summarization.
    """
    template_name = 'diseases/disease_wiki_detail.html'

    def get(self, request):
        query = request.GET.get('q', '').strip()
        if not query:
            messages.warning(request, "Tafadhali ingiza jina la ugonjwa kutafuta.")
            return redirect('diseases:user_dashboard')

        try:
            disease_info = get_disease_info_from_external_apis(query)
            structured = disease_info.get("structured_data", {})
            
            if structured and "error" not in structured:
                # Auto-insert into global Disease library if it doesn't exist
                name_en = disease_info["disease_name_en"]
                name_sw = disease_info["disease_name_sw"]
                
                desc = structured.get('description', {})
                definition = f"{desc.get('definition', '')}\n\n{desc.get('mechanism', '')}"
                
                symptom_data = structured.get('symptoms', {})
                symptoms_str = f"Common: {symptom_data.get('common', '')}. Emergency: {symptom_data.get('emergency', '')}"
                
                prev = structured.get('prevention', {})
                prevention_str = f"Diet: {prev.get('diet', '')}. Vaccine: {prev.get('vaccination', '')}"
                
                treat = structured.get('treatment_options', {})
                treatment_str = f"Meds: {treat.get('medication', '')}. Lifestyle: {treat.get('lifestyle', '')}"

                disease_obj, created = Disease.objects.get_or_create(
                    name__iexact=name_sw,
                    defaults={
                        'name': name_sw,
                        'definition': definition,
                        'symptoms': symptoms_str,
                        'prevention': prevention_str,
                        'treatment': treatment_str,
                        'body_system': structured.get('basic_info', {}).get('body_system', 'General'),
                        'is_chronic': 'Chronic' in structured.get('basic_info', {}).get('category', '')
                    }
                )
                
                return render(request, self.template_name, {
                    'query': query, 
                    'disease_info': disease_info, 
                    'structured': structured,
                    'disease_id': disease_obj.id
                })
            else:
                messages.error(request, "Samahani, hatukuweza kupata maelezo ya ugonjwa huo kwa sasa.")
                return redirect('diseases:user_dashboard')

        except Exception as e:
            messages.error(request, f"Hitilafu imetokea wakati wa kutafuta: {e}")
            return redirect('diseases:user_dashboard')


class DiseaseListCreateApiView(LoginRequiredMixin, View):
    """API to list all global diseases or create a new one."""
    def get(self, request):
        diseases = list(Disease.objects.all().values())
        return JsonResponse({'status': 'success', 'data': diseases})

    def post(self, request):
        # Basic auto-insert logic if data provided via API
        name = request.POST.get('name')
        if name:
            disease, created = Disease.objects.get_or_create(
                name=name,
                defaults={
                    'definition': request.POST.get('definition', ''),
                    'symptoms': request.POST.get('symptoms', ''),
                }
            )
            return JsonResponse({'status': 'success', 'created': created, 'id': disease.id})
        return JsonResponse({'status': 'error', 'message': 'Missing name'}, status=400)


class DiseaseDetailApiView(LoginRequiredMixin, View):
    """API to get details of a specific disease."""
    def get(self, request, disease_id):
        disease = get_object_or_404(Disease, id=disease_id)
        return JsonResponse({'status': 'success', 'data': {
            'id': disease.id,
            'name': disease.name,
            'definition': disease.definition,
            'symptoms': disease.symptoms,
        }})


class DiseaseWhoSearchApiView(LoginRequiredMixin, View):
    """External search API wrapper."""
    def get(self, request):
        query = request.GET.get('q', '')
        data = get_disease_info_from_external_apis(query)
        return JsonResponse({'status': 'success', 'data': data})


class DiseaseWhoDetailApiView(DiseaseWhoSearchApiView):
    """Same as search but can be extended for specific WHO ID lookups."""
    pass