from django.core.management.base import BaseCommand
from django.db import transaction

from diseases.models import Disease
from medics.models import Medication
from django.conf import settings
from django.conf.urls.static import static


MEDICATIONS = [
    {
        'name': 'Paracetamol',
        'generic_name': 'Acetaminophen',
        'description': 'Hutumika kupunguza maumivu ya kawaida na homa. Epuka kuzidisha dozi hasa kwa wenye matatizo ya ini.',
        'dosage': '500mg hadi 1000mg kila baada ya saa 6-8 kulingana na ushauri wa daktari',
        'manufacturer': 'AfyaSmart Sample Pharma',
        'active_ingredients': 'Acetaminophen',
        'rx_required': False,
        'mechanism': 'Paracetamol hufanya kazi kwa kuzuia utengenezaji wa kemikali mwilini (prostaglandins) zinazohusika na maumivu na homa.',
        'side_effects': [
            'Kichefuchefu',
            'Kuvimba kwa ini (kama dozi imezidi)',
            'Mara chache: upele wa ngozi',
        ],
        'faqs': [
            {'q': 'Je, naweza kutumia Paracetamol na chakula?', 'a': 'Ndiyo, unaweza kutumia na au bila chakula.'},
            {'q': 'Nifanye nini nikisahau dozi?', 'a': 'Tumia mara tu unakumbuka, usizidishe dozi.'},
        ],
        'doctor_advice': 'Epuka kuzidisha dozi. Kwa wenye matatizo ya ini, tumia kwa uangalifu na ushauri wa daktari.',
        'did_you_know': 'Paracetamol ni moja ya dawa zinazotumika sana duniani kwa maumivu na homa.',
    },
    {
        'name': 'Amoxicillin',
        'generic_name': 'Amoxicillin',
        'description': 'Antibiotiki inayotumika kwa baadhi ya maambukizi ya bakteria. Tumia tu kwa ushauri wa mtaalamu wa afya.',
        'dosage': '500mg mara 3 kwa siku kwa muda unaoelekezwa',
        'manufacturer': 'East Health Labs',
        'active_ingredients': 'Amoxicillin trihydrate',
        'rx_required': True,
        'mechanism': 'Amoxicillin huzuia ukuaji wa ukuta wa seli za bakteria, hivyo kuua bakteria mwilini.',
        'side_effects': [
            'Kuharisha',
            'Kichefuchefu',
            'Mara chache: mzio (allergy)',
        ],
        'faqs': [
            {'q': 'Je, ni salama kutumia Amoxicillin wakati wa ujauzito?', 'a': 'Kwa kawaida ni salama, lakini wasiliana na daktari kabla ya kutumia.'},
            {'q': 'Nifanye nini nikisahau dozi?', 'a': 'Tumia mara tu unakumbuka, usizidishe dozi.'},
        ],
        'doctor_advice': 'Usitumie antibiotiki bila ushauri wa daktari ili kuepuka usugu wa vimelea.',
        'did_you_know': 'Amoxicillin ni mojawapo ya antibiotiki zinazotumika sana duniani.',
    },
    {
        'name': 'Metformin',
        'generic_name': 'Metformin Hydrochloride',
        'description': 'Hutumika kusaidia kudhibiti sukari kwa baadhi ya watu wenye kisukari aina ya pili.',
        'dosage': '500mg mara 1-2 kwa siku baada ya chakula',
        'manufacturer': 'WellCare Therapeutics',
        'active_ingredients': 'Metformin hydrochloride',
        'rx_required': True,
        'mechanism': 'Metformin hupunguza uzalishaji wa sukari kwenye ini na kuboresha matumizi ya sukari mwilini.',
        'side_effects': [
            'Kuharisha',
            'Maumivu ya tumbo',
            'Kichefuchefu',
        ],
        'faqs': [
            {'q': 'Je, Metformin inaweza kusababisha kupungua uzito?', 'a': 'Ndiyo, baadhi ya watu hupungua uzito wanapotumia Metformin.'},
            {'q': 'Nifanye nini nikisahau dozi?', 'a': 'Ruka dozi hiyo na endelea na ratiba yako.'},
        ],
        'doctor_advice': 'Tumia baada ya chakula ili kupunguza madhara ya tumbo.',
        'did_you_know': 'Metformin ni dawa ya kwanza kupendekezwa kwa kisukari aina ya pili.',
    },
    {
        'name': 'Ibuprofen',
        'generic_name': 'Ibuprofen',
        'description': 'Hupunguza maumivu, uvimbe, na homa. Tahadhari kwa wenye vidonda vya tumbo au matatizo ya figo.',
        'dosage': '200mg hadi 400mg kila baada ya saa 8 baada ya chakula',
        'manufacturer': 'LakeZone Remedies',
        'active_ingredients': 'Ibuprofen',
        'rx_required': False,
        'mechanism': 'Ibuprofen huzuia utengenezaji wa prostaglandins zinazohusika na maumivu na uvimbe.',
        'side_effects': [
            'Maumivu ya tumbo',
            'Kichefuchefu',
            'Vidonda vya tumbo (kama inatumiwa muda mrefu)',
        ],
        'faqs': [
            {'q': 'Je, Ibuprofen inaweza kutumiwa na watoto?', 'a': 'Ndiyo, lakini dozi lazima iwe sahihi na kwa ushauri wa daktari.'},
            {'q': 'Nifanye nini nikisahau dozi?', 'a': 'Tumia mara tu unakumbuka, usizidishe dozi.'},
        ],
        'doctor_advice': 'Epuka kutumia kwa muda mrefu bila ushauri wa daktari.',
        'did_you_know': 'Ibuprofen ni dawa maarufu kwa maumivu ya misuli na maumivu ya hedhi.',
    },
    {
        'name': 'Oral Rehydration Salts',
        'generic_name': 'ORS',
        'description': 'Mchanganyiko wa chumvi na sukari kusaidia kurejesha maji mwilini hasa wakati wa kuharisha au kutapika.',
        'dosage': 'Changanya pakiti moja kulingana na maelekezo na kunywa kidogo kidogo mara kwa mara',
        'manufacturer': 'Community Health Supply',
        'active_ingredients': 'Glucose, sodium chloride, potassium chloride, trisodium citrate',
        'rx_required': False,
        'mechanism': 'ORS husaidia mwili kunyonya maji na madini haraka kupitia utumbo.',
        'side_effects': [
            'Mara chache: kichefuchefu',
            'Kuvimba tumbo (kama inatumiwa vibaya)',
        ],
        'faqs': [
            {'q': 'Je, ORS inaweza kutumiwa na watoto?', 'a': 'Ndiyo, ni salama kwa watoto na watu wazima.'},
            {'q': 'Nifanye nini nikisahau dozi?', 'a': 'Endelea kunywa kidogo kidogo mara kwa mara.'},
        ],
        'doctor_advice': 'Tumia ORS mapema unapoanza dalili za kuharisha au kutapika.',
        'did_you_know': 'ORS imeokoa mamilioni ya maisha duniani kote.',
    },
    {
        'name': 'Salbutamol Inhaler',
        'generic_name': 'Salbutamol',
        'description': 'Husaidia kufungua njia za hewa kwa watu wenye pumu au kubanwa na kifua kwa ghafla.',
        'dosage': 'Pumzi 1-2 wakati wa dalili au kulingana na maelekezo',
        'manufacturer': 'BreathEase Medical',
        'active_ingredients': 'Salbutamol sulfate',
        'rx_required': True,
        'mechanism': 'Salbutamol hufanya kazi kwa kulegeza misuli ya njia za hewa ili kupumua iwe rahisi.',
        'side_effects': [
            'Kutetemeka mikono',
            'Mapigo ya moyo kwenda haraka',
            'Kichwa kuuma',
        ],
        'faqs': [
            {'q': 'Je, Salbutamol inaweza kutumiwa na watoto?', 'a': 'Ndiyo, lakini dozi lazima iwe sahihi na kwa ushauri wa daktari.'},
            {'q': 'Nifanye nini nikisahau dozi?', 'a': 'Tumia mara tu unakumbuka, usizidishe dozi.'},
        ],
        'doctor_advice': 'Tumia inhaler kama ilivyoelekezwa na daktari. Usizidishe dozi.',
        'did_you_know': 'Salbutamol ni dawa muhimu kwa wagonjwa wa pumu duniani kote.',
    },
]

DISEASES = [
    {
        'name': 'Malaria',
        'icd_code': '1F40',
        'definition': 'Malaria ni maambukizi yanayosababishwa na vimelea vinavyoenezwa na mbu aina ya anopheles.',
        'symptoms': 'Homa, kutetemeka, maumivu ya kichwa, udhaifu, jasho, wakati mwingine kutapika.',
        'prevention': 'Tumia chandarua chenye dawa, punguza mazalia ya mbu, vaa nguo za kujikinga hasa usiku.',
        'treatment': 'Fanya kipimo mapema na tumia dawa sahihi kulingana na maelekezo ya mtaalamu wa afya.',
        'complications': [
            'Upungufu wa damu',
            'Koma ya malaria',
            'Kifo (bila matibabu sahihi)',
        ],
        'faqs': [
            {'q': 'Je, malaria inaweza kuzuilika?', 'a': 'Ndiyo, kwa kutumia chandarua na kudhibiti mbu.'},
            {'q': 'Nifanye nini nikipata dalili?', 'a': 'Muone mtaalamu wa afya haraka kwa uchunguzi na matibabu.'},
        ],
        'doctor_advice': 'Usichelewe kutafuta matibabu ukiona dalili za malaria.',
        'did_you_know': 'Malaria bado ni tatizo kubwa Afrika Kusini mwa Jangwa la Sahara.',
    },
    {
        'name': 'Typhoid Fever',
        'icd_code': '1A0Z',
        'definition': 'Typhoid ni maambukizi ya bakteria yanayoathiri mfumo wa chakula na mara nyingi huenezwa kupitia chakula au maji machafu.',
        'symptoms': 'Homa ya muda mrefu, maumivu ya tumbo, uchovu, kuharisha au kufunga choo, kichefuchefu.',
        'prevention': 'Kunywa maji salama, osha mikono mara kwa mara, zingatia usafi wa chakula.',
        'treatment': 'Muone mtaalamu wa afya kwa uchunguzi na dawa sahihi; usitumie antibiotiki bila ushauri.',
        'complications': [
            'Kutoboka kwa utumbo',
            'Maambukizi ya damu',
            'Kifo (bila matibabu sahihi)',
        ],
        'faqs': [
            {'q': 'Je, typhoid inaweza kuzuilika?', 'a': 'Ndiyo, kwa kuzingatia usafi wa chakula na maji.'},
            {'q': 'Nifanye nini nikipata dalili?', 'a': 'Muone daktari haraka kwa uchunguzi na matibabu.'},
        ],
        'doctor_advice': 'Epuka kutumia antibiotiki bila ushauri wa daktari.',
        'did_you_know': 'Typhoid ni tatizo kubwa katika maeneo yenye upungufu wa maji safi.',
    },
    {
        'name': 'Pneumonia',
        'icd_code': 'CA40',
        'definition': 'Pneumonia ni maambukizi ya mapafu yanayoweza kusababishwa na bakteria, virusi, au fangasi.',
        'symptoms': 'Kikohozi, homa, maumivu ya kifua, kupumua kwa shida, uchovu.',
        'prevention': 'Chanjo zinazofaa, kunawa mikono, epuka moshi na mazingira yenye maambukizi mengi.',
        'treatment': 'Matibabu hutegemea chanzo; dalili kali zinahitaji uchunguzi wa haraka hospitalini.',
        'complications': [
            'Kushindwa kupumua',
            'Maambukizi ya damu',
            'Kifo (bila matibabu sahihi)',
        ],
        'faqs': [
            {'q': 'Je, pneumonia inaweza kuzuilika?', 'a': 'Ndiyo, kwa kupata chanjo na kuzingatia usafi.'},
            {'q': 'Nifanye nini nikipata dalili?', 'a': 'Muone daktari haraka kwa uchunguzi na matibabu.'},
        ],
        'doctor_advice': 'Usichelewe kutafuta matibabu ukiona dalili za kupumua kwa shida.',
        'did_you_know': 'Pneumonia ni moja ya sababu kuu za vifo kwa watoto chini ya miaka 5.',
    },
    {
        'name': 'Diabetes Mellitus Type 2',
        'icd_code': '5A11',
        'definition': 'Ni hali ya mwili kushindwa kutumia insulini vizuri na kusababisha sukari kupanda kwenye damu.',
        'symptoms': 'Kiu nyingi, kukojoa mara kwa mara, uchovu, kuona ukungu, vidonda kupona polepole.',
        'prevention': 'Lishe bora, mazoezi ya mara kwa mara, kudhibiti uzito, uchunguzi wa mapema.',
        'treatment': 'Mabadiliko ya maisha na dawa kama metformin au nyingine kulingana na ushauri wa daktari.',
        'complications': [
            'Magonjwa ya moyo',
            'Kiharusi',
            'Ugonjwa wa figo',
        ],
        'faqs': [
            {'q': 'Je, kisukari aina ya pili kinaweza kuzuilika?', 'a': 'Ndiyo, kwa kudhibiti uzito na kufanya mazoezi.'},
            {'q': 'Nifanye nini nikipata dalili?', 'a': 'Muone daktari kwa uchunguzi na ushauri.'},
        ],
        'doctor_advice': 'Fanya uchunguzi wa sukari mara kwa mara na zingatia ushauri wa daktari.',
        'did_you_know': 'Kisukari aina ya pili ni aina ya kisukari inayoongezeka sana duniani.',
    },
    {
        'name': 'Asthma',
        'icd_code': 'CA23',
        'definition': 'Pumu ni ugonjwa wa muda mrefu unaohusisha kubana kwa njia za hewa na kufanya kupumua kuwa kugumu.',
        'symptoms': 'Kupumua kwa shida, sauti ya wheezing, kikohozi hasa usiku, kubana kifua.',
        'prevention': 'Epuka vichochezi kama vumbi, moshi, na harufu kali; fuata mpango wa daktari.',
        'treatment': 'Inhaler za kuondoa dalili na dawa za kudhibiti hali ya mapafu kulingana na tathmini ya daktari.',
        'complications': [
            'Mashambulizi makali ya pumu',
            'Kushindwa kupumua',
        ],
        'faqs': [
            {'q': 'Je, pumu inaweza kuzuilika?', 'a': 'Ndiyo, kwa kuepuka vichochezi na kutumia dawa kama ilivyoelekezwa.'},
            {'q': 'Nifanye nini nikipata dalili?', 'a': 'Tumia inhaler na wasiliana na daktari.'},
        ],
        'doctor_advice': 'Tumia dawa zako kama ilivyoelekezwa na daktari.',
        'did_you_know': 'Pumu inaweza kudhibitiwa vizuri kwa kufuata mpango wa matibabu.',
    },
    {
        'name': 'Urinary Tract Infection',
        'icd_code': 'GB51',
        'definition': 'Ni maambukizi kwenye sehemu za mfumo wa mkojo kama kibofu au njia ya mkojo.',
        'symptoms': 'Maumivu au kuwaka wakati wa kukojoa, kukojoa mara kwa mara, harufu kali ya mkojo, maumivu ya tumbo la chini.',
        'prevention': 'Kunywa maji ya kutosha, zingatia usafi binafsi, usicheleweshe kukojoa.',
        'treatment': 'Fanya uchunguzi na tumia dawa kulingana na ushauri wa mtaalamu wa afya.',
        'complications': [
            'Maambukizi ya figo',
            'Maumivu ya muda mrefu',
        ],
        'faqs': [
            {'q': 'Je, UTI inaweza kuzuilika?', 'a': 'Ndiyo, kwa kunywa maji ya kutosha na kuzingatia usafi.'},
            {'q': 'Nifanye nini nikipata dalili?', 'a': 'Muone daktari kwa uchunguzi na matibabu.'},
        ],
        'doctor_advice': 'Usitumie dawa bila uchunguzi wa daktari.',
        'did_you_know': 'UTI ni mojawapo ya maambukizi ya kawaida kwa wanawake.',
    },
]


class Command(BaseCommand):
    help = 'Seed rich sample medication and disease library data for visual pages and admin usage.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing Medication and Disease records before seeding sample data.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options.get('reset'):
            Medication.objects.all().delete()
            Disease.objects.all().delete()
            self.stdout.write(self.style.WARNING('Existing medical library data cleared.'))

        meds_created = 0
        meds_updated = 0
        for payload in MEDICATIONS:
            _, created = Medication.objects.update_or_create(
                name=payload['name'],
                defaults=payload,
            )
            if created:
                meds_created += 1
            else:
                meds_updated += 1

        diseases_created = 0
        diseases_updated = 0
        for payload in DISEASES:
            _, created = Disease.objects.update_or_create(
                name=payload['name'],
                defaults=payload,
            )
            if created:
                diseases_created += 1
            else:
                diseases_updated += 1

        self.stdout.write(self.style.SUCCESS('✅ Medical library seed complete.'))
        self.stdout.write(
            f'Medications: created {meds_created}, updated {meds_updated}, total {Medication.objects.count()}'
        )
        self.stdout.write(
            f'Diseases: created {diseases_created}, updated {diseases_updated}, total {Disease.objects.count()}'
        )
        self.stdout.write(self.style.WARNING('Run with: python manage.py seed_medical_library --reset'))

urlpatterns = [
    # ... your other url patterns ...
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
