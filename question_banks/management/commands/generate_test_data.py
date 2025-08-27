from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from questions.models import Subject, Topic, Section, Question, QuestionOption, Difficulty
from question_banks.models import QuestionBank, BankQuestion, BankTopicQuota
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Generate test data for question banks'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--clean',
            action='store_true',
            help='Clean existing data before generating new test data',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Generating test data...'))

        # Clean existing data if requested
        if options['clean']:
            self.stdout.write('Cleaning existing test data...')
            # Delete test data in correct order (reverse of creation)
            BankTopicQuota.objects.all().delete()
            BankQuestion.objects.all().delete()
            QuestionBank.objects.filter(name__in=['Matematika Asoslari', 'Fizika Fundamentlari']).delete()
            QuestionOption.objects.filter(question__created_by__username='creator_test').delete()
            Question.objects.filter(created_by__username='creator_test').delete()
            Section.objects.filter(topic__subject__name__in=['Matematika', 'Fizika']).delete()
            Topic.objects.filter(subject__name__in=['Matematika', 'Fizika']).delete()
            Subject.objects.filter(name__in=['Matematika', 'Fizika']).delete()
            User.objects.filter(username__in=['expert_test', 'creator_test']).delete()
            self.stdout.write(self.style.SUCCESS('Cleaned existing test data'))

        # Get existing difficulties
        try:
            easy = Difficulty.objects.get(code='EASY')
            medium = Difficulty.objects.get(code='MEDIUM') 
            hard = Difficulty.objects.get(code='HARD')
        except Difficulty.DoesNotExist:
            self.stdout.write(self.style.ERROR('Required difficulties not found. Please run migrations first.'))
            return

        # Get or create subjects
        math_subject, _ = Subject.objects.get_or_create(
            name='Matematika',
            defaults={'code': 'MATH', 'description': 'Matematika fani'}
        )
        
        physics_subject, _ = Subject.objects.get_or_create(
            name='Fizika', 
            defaults={'code': 'PHYS', 'description': 'Fizika fani'}
        )

        # Create topics for Math
        math_topics_data = [
            ('Algebra', 'Algebraik ifodalar'),
            ('Geometriya', 'Geometrik shakllar'),
            ('Trigonometriya', 'Trigonometrik funksiyalar'),
            ('Kalkulus', 'Differensial va integral'),
            ('Statistika', 'Ma\'lumotlarni tahlil qilish'),
            ('Ehtimollik', 'Ehtimollar nazariyasi'),
        ]

        math_topics = []
        for i, (topic_name, topic_desc) in enumerate(math_topics_data, 1):
            topic, _ = Topic.objects.get_or_create(
                name=topic_name,
                subject=math_subject,
                number=i,
                defaults={'description': topic_desc}
            )
            math_topics.append(topic)

        # Create topics for Physics
        physics_topics_data = [
            ('Mexanika', 'Jismlarning harakati'),
            ('Termodinamika', 'Issiqlik va energiya'),
            ('Elektromagnetizm', 'Elektr va magnit maydonlar'),
            ('Optika', 'Yorug\'lik hodisalari'),
            ('Atom fizikasi', 'Atom va molekula tuzilishi'),
        ]

        physics_topics = []
        for i, (topic_name, topic_desc) in enumerate(physics_topics_data, 1):
            topic, _ = Topic.objects.get_or_create(
                name=topic_name,
                subject=physics_subject,
                number=i,
                defaults={'description': topic_desc}
            )
            physics_topics.append(topic)

        # Create sections for each topic
        sections_data = {
            'Algebra': ['Tenglamalar', 'Tengsizliklar', 'Funksiyalar'],
            'Geometriya': ['Planimetriya', 'Stereometriya', 'Analitik geometriya'],
            'Trigonometriya': ['Asosiy funksiyalar', 'Identifikatsiyalar', 'Tenglamalar'],
            'Mexanika': ['Kinematika', 'Dinamika', 'Statika'],
            'Termodinamika': ['Issiqlik o\'tkazuvchanlik', 'Gazlar qonuni', 'Entropiya'],
        }

        all_sections = []
        for topic in math_topics + physics_topics:
            if topic.name in sections_data:
                for i, section_name in enumerate(sections_data[topic.name], 1):
                    section, _ = Section.objects.get_or_create(
                        name=section_name,
                        topic=topic,
                        number=i,
                        defaults={'description': f'{section_name} bo\'yicha masalalar'}
                    )
                    all_sections.append(section)

        # Get or create expert user
        expert_user, created = User.objects.get_or_create(
            username='expert_test',
            defaults={
                'first_name': 'Test',
                'last_name': 'Expert',
                'email': 'expert@test.com',
                'role': User.Role.Q_EXPERT,
                'is_active': True
            }
        )

        # Get or create creator user
        creator_user, created = User.objects.get_or_create(
            username='creator_test',
            defaults={
                'first_name': 'Test',
                'last_name': 'Creator',
                'email': 'creator@test.com',
                'role': User.Role.CREATOR,
                'is_active': True
            }
        )

        # Sample questions data
        math_questions_data = [
            # Algebra - Easy
            {
                'text': '2x + 5 = 13 tenglamani yeching',
                'difficulty': easy,
                'topic': 'Algebra',
                'section': 'Tenglamalar',
                'options': [
                    {'text': 'x = 4', 'is_correct': True},
                    {'text': 'x = 3', 'is_correct': False},
                    {'text': 'x = 5', 'is_correct': False},
                    {'text': 'x = 6', 'is_correct': False},
                ]
            },
            {
                'text': '3(x - 2) = 15 tenglamani yeching',
                'difficulty': easy,
                'topic': 'Algebra',
                'section': 'Tenglamalar',
                'options': [
                    {'text': 'x = 7', 'is_correct': True},
                    {'text': 'x = 5', 'is_correct': False},
                    {'text': 'x = 6', 'is_correct': False},
                    {'text': 'x = 8', 'is_correct': False},
                ]
            },
            {
                'text': 'x² = 16 tenglamaning yechimlarini toping',
                'difficulty': easy,
                'topic': 'Algebra',
                'section': 'Tenglamalar',
                'options': [
                    {'text': 'x = ±4', 'is_correct': True},
                    {'text': 'x = 4', 'is_correct': False},
                    {'text': 'x = 8', 'is_correct': False},
                    {'text': 'x = ±8', 'is_correct': False},
                ]
            },
            # Algebra - Medium
            {
                'text': 'f(x) = x² + 2x - 3 funksiyaning minimumini toping',
                'difficulty': medium,
                'topic': 'Algebra',
                'section': 'Funksiyalar',
                'options': [
                    {'text': 'x = -1', 'is_correct': True},
                    {'text': 'x = 0', 'is_correct': False},
                    {'text': 'x = 1', 'is_correct': False},
                    {'text': 'x = -2', 'is_correct': False},
                ]
            },
            {
                'text': 'x² - 5x + 6 = 0 kvadrat tenglamani yeching',
                'difficulty': medium,
                'topic': 'Algebra',
                'section': 'Tenglamalar',
                'options': [
                    {'text': 'x = 2, x = 3', 'is_correct': True},
                    {'text': 'x = 1, x = 6', 'is_correct': False},
                    {'text': 'x = -2, x = -3', 'is_correct': False},
                    {'text': 'x = 0, x = 5', 'is_correct': False},
                ]
            },
            # Algebra - Hard
            {
                'text': 'f(x) = 2x³ - 6x² + 6x - 2 funksiyaning hosilasini toping',
                'difficulty': hard,
                'topic': 'Algebra',
                'section': 'Funksiyalar',
                'options': [
                    {'text': "f'(x) = 6x² - 12x + 6", 'is_correct': True},
                    {'text': "f'(x) = 6x² - 12x + 2", 'is_correct': False},
                    {'text': "f'(x) = 2x² - 6x + 6", 'is_correct': False},
                    {'text': "f'(x) = 6x² - 6x + 6", 'is_correct': False},
                ]
            },
            
            # Geometriya - Easy
            {
                'text': 'To\'g\'ri burchakli uchburchakning katetlari 3 va 4 ga teng. Gipotenuzani toping.',
                'difficulty': easy,
                'topic': 'Geometriya',
                'section': 'Planimetriya',
                'options': [
                    {'text': '5', 'is_correct': True},
                    {'text': '7', 'is_correct': False},
                    {'text': '6', 'is_correct': False},
                    {'text': '8', 'is_correct': False},
                ]
            },
            {
                'text': 'Kvadratning tomoni 6 sm. Uning yuzasini toping.',
                'difficulty': easy,
                'topic': 'Geometriya',
                'section': 'Planimetriya',
                'options': [
                    {'text': '36 sm²', 'is_correct': True},
                    {'text': '24 sm²', 'is_correct': False},
                    {'text': '12 sm²', 'is_correct': False},
                    {'text': '18 sm²', 'is_correct': False},
                ]
            },
            {
                'text': 'To\'g\'ri to\'rtburchakning bo\'yi 8 sm, eni 5 sm. Perimetrini toping.',
                'difficulty': easy,
                'topic': 'Geometriya',
                'section': 'Planimetriya',
                'options': [
                    {'text': '26 sm', 'is_correct': True},
                    {'text': '40 sm', 'is_correct': False},
                    {'text': '13 sm', 'is_correct': False},
                    {'text': '24 sm', 'is_correct': False},
                ]
            },
            # Geometriya - Medium
            {
                'text': 'Doiraning yuzasi πr² formula bilan topiladi. r = 5 bo\'lganda yuza nechaga teng?',
                'difficulty': medium,
                'topic': 'Geometriya',
                'section': 'Planimetriya',
                'options': [
                    {'text': '25π', 'is_correct': True},
                    {'text': '10π', 'is_correct': False},
                    {'text': '5π', 'is_correct': False},
                    {'text': '50π', 'is_correct': False},
                ]
            },
            {
                'text': 'Kubning qirrasi 4 sm. Uning hajmini toping.',
                'difficulty': medium,
                'topic': 'Geometriya',
                'section': 'Stereometriya',
                'options': [
                    {'text': '64 sm³', 'is_correct': True},
                    {'text': '48 sm³', 'is_correct': False},
                    {'text': '16 sm³', 'is_correct': False},
                    {'text': '32 sm³', 'is_correct': False},
                ]
            },
            # Geometriya - Hard
            {
                'text': 'Shar radiusi 3 sm. Uning hajmini toping (V = (4/3)πr³)',
                'difficulty': hard,
                'topic': 'Geometriya',
                'section': 'Stereometriya',
                'options': [
                    {'text': '36π sm³', 'is_correct': True},
                    {'text': '27π sm³', 'is_correct': False},
                    {'text': '12π sm³', 'is_correct': False},
                    {'text': '9π sm³', 'is_correct': False},
                ]
            },
            
            # Trigonometriya - Easy
            {
                'text': 'sin(30°) ning qiymati nechaga teng?',
                'difficulty': easy,
                'topic': 'Trigonometriya',
                'section': 'Asosiy funksiyalar',
                'options': [
                    {'text': '1/2', 'is_correct': True},
                    {'text': '√3/2', 'is_correct': False},
                    {'text': '1', 'is_correct': False},
                    {'text': '√2/2', 'is_correct': False},
                ]
            },
            {
                'text': 'cos(60°) ning qiymati nechaga teng?',
                'difficulty': easy,
                'topic': 'Trigonometriya',
                'section': 'Asosiy funksiyalar',
                'options': [
                    {'text': '1/2', 'is_correct': True},
                    {'text': '√3/2', 'is_correct': False},
                    {'text': '√2/2', 'is_correct': False},
                    {'text': '1', 'is_correct': False},
                ]
            },
            {
                'text': 'tan(45°) ning qiymati nechaga teng?',
                'difficulty': easy,
                'topic': 'Trigonometriya',
                'section': 'Asosiy funksiyalar',
                'options': [
                    {'text': '1', 'is_correct': True},
                    {'text': '√2', 'is_correct': False},
                    {'text': '1/2', 'is_correct': False},
                    {'text': '√3', 'is_correct': False},
                ]
            },
            # Trigonometriya - Medium
            {
                'text': 'sin²x + cos²x ifodaning qiymatini toping',
                'difficulty': medium,
                'topic': 'Trigonometriya',
                'section': 'Identifikatsiyalar',
                'options': [
                    {'text': '1', 'is_correct': True},
                    {'text': '0', 'is_correct': False},
                    {'text': '2', 'is_correct': False},
                    {'text': 'π', 'is_correct': False},
                ]
            },
            {
                'text': 'sin(90° - α) ifodasi nimaga teng?',
                'difficulty': medium,
                'topic': 'Trigonometriya',
                'section': 'Identifikatsiyalar',
                'options': [
                    {'text': 'cos(α)', 'is_correct': True},
                    {'text': 'sin(α)', 'is_correct': False},
                    {'text': 'tan(α)', 'is_correct': False},
                    {'text': '1 - sin(α)', 'is_correct': False},
                ]
            },
            # Trigonometriya - Hard
            {
                'text': 'cos²x + sin²x ifoda qanday qiymatga teng?',
                'difficulty': hard,
                'topic': 'Trigonometriya',
                'section': 'Identifikatsiyalar',
                'options': [
                    {'text': '1', 'is_correct': True},
                    {'text': '0', 'is_correct': False},
                    {'text': '2', 'is_correct': False},
                    {'text': 'π', 'is_correct': False},
                ]
            },
            
            # Statistika - Easy
            {
                'text': '2, 4, 6, 8, 10 sonlarining o\'rta arifmetigini toping',
                'difficulty': easy,
                'topic': 'Statistika',
                'section': 'Ma\'lumotlarni tahlil qilish',
                'options': [
                    {'text': '6', 'is_correct': True},
                    {'text': '5', 'is_correct': False},
                    {'text': '7', 'is_correct': False},
                    {'text': '8', 'is_correct': False},
                ]
            },
            # Statistika - Medium
            {
                'text': '1, 3, 5, 7, 9 sonlarining dispersiyasini toping',
                'difficulty': medium,
                'topic': 'Statistika',
                'section': 'Ma\'lumotlarni tahlil qilish',
                'options': [
                    {'text': '8', 'is_correct': True},
                    {'text': '5', 'is_correct': False},
                    {'text': '10', 'is_correct': False},
                    {'text': '6', 'is_correct': False},
                ]
            },
            
            # Ehtimollik - Easy
            {
                'text': 'Tanga tashlanganda "raqam" chiqish ehtimoli qancha?',
                'difficulty': easy,
                'topic': 'Ehtimollik',
                'section': 'Ehtimollar nazariyasi',
                'options': [
                    {'text': '1/2', 'is_correct': True},
                    {'text': '1/4', 'is_correct': False},
                    {'text': '1', 'is_correct': False},
                    {'text': '1/3', 'is_correct': False},
                ]
            },
        ]

        physics_questions_data = [
            # Mexanika - Easy
            {
                'text': 'Jismning tezligi 10 m/s, vaqt 5 s. Yo\'lni toping.',
                'difficulty': easy,
                'topic': 'Mexanika',
                'section': 'Kinematika',
                'options': [
                    {'text': '50 m', 'is_correct': True},
                    {'text': '15 m', 'is_correct': False},
                    {'text': '2 m', 'is_correct': False},
                    {'text': '500 m', 'is_correct': False},
                ]
            },
            {
                'text': 'Jism 20 m/s tezlik bilan harakatlanmoqda. 10 soniyadan keyin qancha yo\'l bosadi?',
                'difficulty': easy,
                'topic': 'Mexanika',
                'section': 'Kinematika',
                'options': [
                    {'text': '200 m', 'is_correct': True},
                    {'text': '30 m', 'is_correct': False},
                    {'text': '2 m', 'is_correct': False},
                    {'text': '100 m', 'is_correct': False},
                ]
            },
            {
                'text': 'Massasi 5 kg bo\'lgan jismga 20 N kuch ta\'sir qilsa, tezlanish nechaga teng? (F = ma)',
                'difficulty': easy,
                'topic': 'Mexanika',
                'section': 'Dinamika',
                'options': [
                    {'text': '4 m/s²', 'is_correct': True},
                    {'text': '25 m/s²', 'is_correct': False},
                    {'text': '100 m/s²', 'is_correct': False},
                    {'text': '15 m/s²', 'is_correct': False},
                ]
            },
            # Mexanika - Medium
            {
                'text': 'Jism 0 dan 30 m/s gacha 6 soniyada tezlashdi. Tezlanishni toping.',
                'difficulty': medium,
                'topic': 'Mexanika',
                'section': 'Kinematika',
                'options': [
                    {'text': '5 m/s²', 'is_correct': True},
                    {'text': '180 m/s²', 'is_correct': False},
                    {'text': '24 m/s²', 'is_correct': False},
                    {'text': '36 m/s²', 'is_correct': False},
                ]
            },
            {
                'text': 'Massasi 2 kg bo\'lgan jismning kinetik energiyasi 50 J. Tezligini toping. (E = mv²/2)',
                'difficulty': medium,
                'topic': 'Mexanika',
                'section': 'Dinamika',
                'options': [
                    {'text': '10 m/s', 'is_correct': True},
                    {'text': '25 m/s', 'is_correct': False},
                    {'text': '5 m/s', 'is_correct': False},
                    {'text': '50 m/s', 'is_correct': False},
                ]
            },
            # Mexanika - Hard
            {
                'text': 'Jism 100 m balandlikdan erkin tushmoqda. Yerga tegishidan oldingi tezligi qancha? (g = 10 m/s²)',
                'difficulty': hard,
                'topic': 'Mexanika',
                'section': 'Kinematika',
                'options': [
                    {'text': '√2000 m/s ≈ 44.7 m/s', 'is_correct': True},
                    {'text': '1000 m/s', 'is_correct': False},
                    {'text': '200 m/s', 'is_correct': False},
                    {'text': '10 m/s', 'is_correct': False},
                ]
            },
            
            # Termodinamika - Easy
            {
                'text': 'Suvning qaynash harorati normal bosimda necha gradus?',
                'difficulty': easy,
                'topic': 'Termodinamika',
                'section': 'Issiqlik o\'tkazuvchanlik',
                'options': [
                    {'text': '100°C', 'is_correct': True},
                    {'text': '0°C', 'is_correct': False},
                    {'text': '50°C', 'is_correct': False},
                    {'text': '273°C', 'is_correct': False},
                ]
            },
            {
                'text': 'Muzning erish harorati necha gradus?',
                'difficulty': easy,
                'topic': 'Termodinamika',
                'section': 'Issiqlik o\'tkazuvchanlik',
                'options': [
                    {'text': '0°C', 'is_correct': True},
                    {'text': '100°C', 'is_correct': False},
                    {'text': '-100°C', 'is_correct': False},
                    {'text': '32°C', 'is_correct': False},
                ]
            },
            # Termodinamika - Medium
            {
                'text': 'Gazning bosimi 2 atm, hajmi 3 l. Harorat o\'zgarmaganda hajm 6 l bo\'lsa, bosim qanday bo\'ladi?',
                'difficulty': medium,
                'topic': 'Termodinamika',
                'section': 'Gazlar qonuni',
                'options': [
                    {'text': '1 atm', 'is_correct': True},
                    {'text': '4 atm', 'is_correct': False},
                    {'text': '6 atm', 'is_correct': False},
                    {'text': '0.5 atm', 'is_correct': False},
                ]
            },
            {
                'text': 'Ideal gazning hajmi 4 l, bosimi 2 atm. Bosim 8 atm ga oshirilsa, hajm qanday bo\'ladi? (T = const)',
                'difficulty': medium,
                'topic': 'Termodinamika',
                'section': 'Gazlar qonuni',
                'options': [
                    {'text': '1 l', 'is_correct': True},
                    {'text': '16 l', 'is_correct': False},
                    {'text': '32 l', 'is_correct': False},
                    {'text': '2 l', 'is_correct': False},
                ]
            },
            # Termodinamika - Hard
            {
                'text': '1 mol ideal gazning harorati 300 K dan 600 K ga oshirildi. Ichki energiyaning o\'zgarishini toping. (ΔU = (3/2)nRΔT, R = 8.31 J/mol·K)',
                'difficulty': hard,
                'topic': 'Termodinamika',
                'section': 'Gazlar qonuni',
                'options': [
                    {'text': '3739.5 J', 'is_correct': True},
                    {'text': '2493 J', 'is_correct': False},
                    {'text': '4986 J', 'is_correct': False},
                    {'text': '1247 J', 'is_correct': False},
                ]
            },
            
            # Optika - Easy
            {
                'text': 'Nur ko\'zguda qanday qaytadi?',
                'difficulty': easy,
                'topic': 'Optika',
                'section': 'Yorug\'lik hodisalari',
                'options': [
                    {'text': 'Tushish burchagi = qaytish burchagi', 'is_correct': True},
                    {'text': 'Har xil burchak ostida', 'is_correct': False},
                    {'text': 'Faqat 90° burchak ostida', 'is_correct': False},
                    {'text': 'Qaytmaydi', 'is_correct': False},
                ]
            },
            {
                'text': 'Qaysi rang eng qisqa to\'lqin uzunligiga ega?',
                'difficulty': easy,
                'topic': 'Optika',
                'section': 'Yorug\'lik hodisalari',
                'options': [
                    {'text': 'Binafsha', 'is_correct': True},
                    {'text': 'Qizil', 'is_correct': False},
                    {'text': 'Yashil', 'is_correct': False},
                    {'text': 'Sariq', 'is_correct': False},
                ]
            },
            # Optika - Medium
            {
                'text': 'Yorug\'likning vakuumdagi tezligi qancha?',
                'difficulty': medium,
                'topic': 'Optika',
                'section': 'Yorug\'lik hodisalari',
                'options': [
                    {'text': '3×10⁸ m/s', 'is_correct': True},
                    {'text': '3×10⁶ m/s', 'is_correct': False},
                    {'text': '3×10¹⁰ m/s', 'is_correct': False},
                    {'text': '3×10⁷ m/s', 'is_correct': False},
                ]
            },
            {
                'text': 'Suvda yorug\'lik sindirish ko\'rsatkichi 1.33. Vakuumdan suvga o\'tganda tezlik qanday o\'zgaradi?',
                'difficulty': medium,
                'topic': 'Optika',
                'section': 'Yorug\'lik hodisalari',
                'options': [
                    {'text': '1.33 marta kamayadi', 'is_correct': True},
                    {'text': '1.33 marta ortadi', 'is_correct': False},
                    {'text': 'O\'zgarmaydi', 'is_correct': False},
                    {'text': '2 marta kamayadi', 'is_correct': False},
                ]
            },
            
            # Elektromagnetizm - Easy
            {
                'text': 'Elektr zanjirida kuchlanish 12 V, qarshilik 4 Ω. Tok kuchini toping. (U = IR)',
                'difficulty': easy,
                'topic': 'Elektromagnetizm',
                'section': 'Elektr va magnit maydonlar',
                'options': [
                    {'text': '3 A', 'is_correct': True},
                    {'text': '16 A', 'is_correct': False},
                    {'text': '8 A', 'is_correct': False},
                    {'text': '48 A', 'is_correct': False},
                ]
            },
            # Elektromagnetizm - Medium
            {
                'text': 'Ikkita musbat zaryad orasidagi masofa 2 marta oshirilsa, ular orasidagi kuch qanday o\'zgaradi?',
                'difficulty': medium,
                'topic': 'Elektromagnetizm',
                'section': 'Elektr va magnit maydonlar',
                'options': [
                    {'text': '4 marta kamayadi', 'is_correct': True},
                    {'text': '2 marta kamayadi', 'is_correct': False},
                    {'text': '4 marta ortadi', 'is_correct': False},
                    {'text': 'O\'zgarmaydi', 'is_correct': False},
                ]
            },
            
            # Atom fizikasi - Easy
            {
                'text': 'Atomning markazida nima joylashgan?',
                'difficulty': easy,
                'topic': 'Atom fizikasi',
                'section': 'Atom va molekula tuzilishi',
                'options': [
                    {'text': 'Yadro', 'is_correct': True},
                    {'text': 'Elektron', 'is_correct': False},
                    {'text': 'Neytron', 'is_correct': False},
                    {'text': 'Foton', 'is_correct': False},
                ]
            },
            # Atom fizikasi - Medium
            {
                'text': 'Vodorod atomida elektron energiyasi -13.6 eV. Ikkinchi energetik sathda energiya nechaga teng?',
                'difficulty': medium,
                'topic': 'Atom fizikasi',
                'section': 'Atom va molekula tuzilishi',
                'options': [
                    {'text': '-3.4 eV', 'is_correct': True},
                    {'text': '-6.8 eV', 'is_correct': False},
                    {'text': '-27.2 eV', 'is_correct': False},
                    {'text': '-1.51 eV', 'is_correct': False},
                ]
            },
        ]

        # Create questions
        created_questions = []
        all_questions_data = math_questions_data + physics_questions_data

        for q_data in all_questions_data:
            # Find topic and section
            topic = None
            section = None
            
            if q_data['topic'] in [t.name for t in math_topics]:
                topic = next(t for t in math_topics if t.name == q_data['topic'])
            else:
                topic = next(t for t in physics_topics if t.name == q_data['topic'])
            
            if all_sections:
                section = next((s for s in all_sections if s.name == q_data['section'] and s.topic == topic), None)

            question, created = Question.objects.get_or_create(
                text=q_data['text'],
                defaults={
                    'topic': topic,
                    'section': section,
                    'difficulty': q_data['difficulty'],
                    'created_by': creator_user,
                    'reviewed_by': expert_user,
                    'status': 'APPROVED',
                }
            )

            if created:
                # Create options for the question
                for order, opt_data in enumerate(q_data['options'], 1):
                    QuestionOption.objects.create(
                        question=question,
                        text=opt_data['text'],
                        is_correct=opt_data['is_correct'],
                        order=order
                    )
                created_questions.append(question)

        self.stdout.write(f'Created {len(created_questions)} questions')

        # Create question banks
        banks_data = [
            {
                'name': 'Matematika Asoslari',
                'description': 'Matematik asoslarni o\'rganish uchun savol to\'plami',
                'subject': math_subject,
                'expert': expert_user
            },
            {
                'name': 'Fizika Fundamentlari', 
                'description': 'Fizika fanining asosiy qonunlari',
                'subject': physics_subject,
                'expert': expert_user
            }
        ]

        created_banks = []
        for bank_data in banks_data:
            bank, created = QuestionBank.objects.get_or_create(
                name=bank_data['name'],
                defaults=bank_data
            )
            created_banks.append(bank)

        self.stdout.write(f'Created {len(created_banks)} question banks')

        # Add questions to banks and create quotas
        math_bank = created_banks[0]
        physics_bank = created_banks[1] if len(created_banks) > 1 else None

        # Add math questions to math bank
        math_questions = [q for q in created_questions if q.topic in math_topics]
        for question in math_questions:
            BankQuestion.objects.get_or_create(
                bank=math_bank,
                question=question,
                defaults={'added_by': expert_user}
            )

            # Create topic quotas
            BankTopicQuota.objects.get_or_create(
                bank=math_bank,
                topic=question.topic,
                section=question.section,
                difficulty=question.difficulty,
                defaults={'target_count': random.randint(2, 5), 'current_count': 1}
            )

        # Add physics questions to physics bank
        if physics_bank:
            physics_questions = [q for q in created_questions if q.topic in physics_topics]
            for question in physics_questions:
                BankQuestion.objects.get_or_create(
                    bank=physics_bank,
                    question=question,
                    defaults={'added_by': expert_user}
                )

                # Create topic quotas
                BankTopicQuota.objects.get_or_create(
                    bank=physics_bank,
                    topic=question.topic,
                    section=question.section,
                    difficulty=question.difficulty,
                    defaults={'target_count': random.randint(2, 5), 'current_count': 1}
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully generated test data:\n'
                f'- {len(math_topics + physics_topics)} topics\n'
                f'- {len(all_sections)} sections\n' 
                f'- {len(created_questions)} questions\n'
                f'- {len(created_banks)} question banks\n'
                f'- Added questions to banks with quotas'
            )
        )