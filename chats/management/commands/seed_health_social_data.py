import random
from html import escape
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from menstrual.models import CommunityGroup, CommunityPost, CommunityStatus
from users.models import UserAIPersona


HEALTH_TOPICS = [
    "hydration habits",
    "balanced nutrition",
    "blood pressure awareness",
    "heart healthy lifestyle",
    "diabetes prevention",
    "mental wellness check",
    "sleep hygiene",
    "stress management",
    "exercise consistency",
    "healthy pregnancy nutrition",
    "menstrual health education",
    "reproductive health awareness",
    "postpartum recovery",
    "child vaccination reminders",
    "healthy weight management",
    "immune system support",
    "anemia prevention",
    "healthy skin care",
    "oral health routine",
    "healthy aging care",
]

POST_TEMPLATES = [
    "Today I am focusing on {topic}. Small daily habits make a big health difference.",
    "Health tip: {topic}. Start simple, stay consistent, and monitor your progress.",
    "Community reminder on {topic}: prevention and early action protect long-term health.",
    "My weekly health focus is {topic}. Sharing this to encourage everyone in the group.",
    "Let us discuss {topic} and practical ways to improve outcomes in daily life.",
]

GROUP_NAME_PREFIX = "Health Group"
USER_PREFIX = "test_health_user"
BOT_MALE = "health_bot_male"
BOT_FEMALE = "health_bot_female"


class Command(BaseCommand):
    help = (
        "Creates test community data: users, groups, image-based health posts, "
        "and male/female bot accounts."
    )

    def add_arguments(self, parser):
        parser.add_argument("--users", type=int, default=50, help="Number of regular accounts to create (default: 50)")
        parser.add_argument("--groups", type=int, default=50, help="Number of groups to create (default: 50)")
        parser.add_argument("--posts-per-user", type=int, default=10, help="Posts per account (default: 10)")
        parser.add_argument("--statuses-per-user", type=int, default=2, help="Statuses per account (default: 2)")
        parser.add_argument("--password", type=str, default="AfyaTest@123", help="Password for created users")
        parser.add_argument(
            "--image-source",
            choices=["svg", "online"],
            default="svg",
            help="Image generation mode: svg (fast/local, default) or online (download placeholders)",
        )
        parser.add_argument(
            "--online-timeout",
            type=int,
            default=6,
            help="Timeout in seconds per online image request (default: 6)",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete previously generated seed data (users/groups/posts/statuses from this command) before creating new data",
        )

    def handle(self, *args, **options):
        random.seed(42)
        user_count = max(1, options["users"])
        group_count = max(1, options["groups"])
        posts_per_user = max(1, options["posts_per_user"])
        statuses_per_user = max(0, options["statuses_per_user"])
        password = options["password"]
        do_reset = options["reset"]
        self.image_source = options["image_source"]
        self.online_timeout = max(2, int(options["online_timeout"]))

        User = get_user_model()
        image_cache = {}

        with transaction.atomic():
            if do_reset:
                self._reset_seed_data(User)

            users = self._create_regular_users(User, user_count, password)
            bots = self._create_bots(User, password)
            all_accounts = users + bots

            groups = self._create_groups(group_count, all_accounts)
            self._assign_group_memberships(groups, all_accounts)

            posts_created = self._create_posts(all_accounts, groups, posts_per_user, image_cache)
            statuses_created = self._create_statuses(all_accounts, groups, statuses_per_user, image_cache)

        self.stdout.write(self.style.SUCCESS("✅ Seed complete."))
        self.stdout.write(f"Users created/updated: {len(users)} regular + {len(bots)} bots")
        self.stdout.write(f"Groups created/updated: {len(groups)}")
        self.stdout.write(f"Posts created: {posts_created}")
        self.stdout.write(f"Statuses created: {statuses_created}")
        self.stdout.write(f"Default password: {password}")
        self.stdout.write(self.style.WARNING("Run with: python manage.py seed_health_social_data"))

    def _reset_seed_data(self, User):
        self.stdout.write("Resetting previous seeded data...")

        seeded_usernames = [f"{USER_PREFIX}_{i:03d}" for i in range(1, 1000)] + [BOT_MALE, BOT_FEMALE]
        seeded_users = User.objects.filter(username__in=seeded_usernames)

        CommunityStatus.objects.filter(user__in=seeded_users).delete()
        CommunityPost.objects.filter(user__in=seeded_users).delete()
        CommunityGroup.objects.filter(name__startswith=GROUP_NAME_PREFIX).delete()
        UserAIPersona.objects.filter(user__in=seeded_users).delete()
        seeded_users.delete()

    def _create_regular_users(self, User, user_count, password):
        users = []
        for i in range(1, user_count + 1):
            username = f"{USER_PREFIX}_{i:03d}"
            email = f"{username}@example.com"
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": email,
                    "first_name": f"Health{i}",
                    "last_name": "Tester",
                    "is_active": True,
                },
            )
            if created or not user.has_usable_password():
                user.set_password(password)
                user.save(update_fields=["password"])

            gender = "female" if i % 2 == 0 else "male"
            self._upsert_persona(user, gender)
            users.append(user)

        return users

    def _create_bots(self, User, password):
        bot_defs = [
            (BOT_FEMALE, "female", "Afya", "WomenBot"),
            (BOT_MALE, "male", "Afya", "MenBot"),
        ]
        bots = []
        for username, gender, first_name, last_name in bot_defs:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@example.com",
                    "first_name": first_name,
                    "last_name": last_name,
                    "is_active": True,
                },
            )
            if created or not user.has_usable_password():
                user.set_password(password)
                user.save(update_fields=["password"])

            self._upsert_persona(user, gender, as_bot=True)
            bots.append(user)

        return bots

    def _upsert_persona(self, user, gender, as_bot=False):
        bio = (
            "Automated health community bot account for testing female feed and responses."
            if gender == "female"
            else "Automated health community bot account for testing male feed and responses."
        )
        if not as_bot:
            bio = f"Test account profile focusing on {random.choice(HEALTH_TOPICS)}."

        persona, _ = UserAIPersona.objects.get_or_create(user=user)
        persona.gender = gender
        persona.age = persona.age or random.randint(20, 42)
        persona.height_cm = persona.height_cm or random.randint(150, 185)
        persona.weight_kg = persona.weight_kg or round(random.uniform(52, 90), 1)
        persona.health_notes = persona.health_notes or "General wellness follow-up"
        persona.permanent_diseases = persona.permanent_diseases or "None reported"
        persona.medications = persona.medications or "No daily medication"
        persona.lifestyle_notes = persona.lifestyle_notes or "Light exercise and hydration tracking"
        persona.sleep_hours = persona.sleep_hours or round(random.uniform(6.0, 8.0), 1)
        persona.stress_level = persona.stress_level or random.choice(["low", "moderate"])
        persona.exercise_frequency = persona.exercise_frequency or random.choice(["light", "moderate"])
        persona.bio = bio
        persona.update_quality_metrics(save=False)
        persona.save()

    def _create_groups(self, group_count, users):
        groups = []
        users_by_gender = {
            "female": [u for u in users if getattr(getattr(u, "ai_persona", None), "gender", "") == "female"],
            "male": [u for u in users if getattr(getattr(u, "ai_persona", None), "gender", "") == "male"],
        }

        for i in range(1, group_count + 1):
            gender = "female" if i % 2 == 0 else "male"
            creator_pool = users_by_gender.get(gender) or users
            creator = random.choice(creator_pool)
            topic = HEALTH_TOPICS[(i - 1) % len(HEALTH_TOPICS)]
            name = f"{GROUP_NAME_PREFIX} {i:02d}"

            group, _ = CommunityGroup.objects.get_or_create(
                name=name,
                audience_gender=gender,
                defaults={
                    "description": f"Focused discussion on {topic} with practical health advice.",
                    "created_by": creator,
                    "require_join_approval": random.choice([False, False, True]),
                },
            )
            group.members.add(creator)
            groups.append(group)

        return groups

    def _assign_group_memberships(self, groups, users):
        users_by_gender = {
            "female": [u for u in users if getattr(getattr(u, "ai_persona", None), "gender", "") == "female"],
            "male": [u for u in users if getattr(getattr(u, "ai_persona", None), "gender", "") == "male"],
        }

        for group in groups:
            pool = users_by_gender.get(group.audience_gender, [])
            if not pool:
                continue
            sample_size = min(len(pool), random.randint(8, 20))
            for member in random.sample(pool, sample_size):
                group.members.add(member)

    def _create_posts(self, users, groups, posts_per_user, image_cache):
        groups_by_gender = {
            "female": [g for g in groups if g.audience_gender == "female"],
            "male": [g for g in groups if g.audience_gender == "male"],
        }

        total_posts = 0

        for user in users:
            gender = getattr(getattr(user, "ai_persona", None), "gender", None) or "female"
            eligible_groups = groups_by_gender.get(gender) or groups

            for index in range(posts_per_user):
                topic = HEALTH_TOPICS[(index + random.randint(0, 1000)) % len(HEALTH_TOPICS)]
                content = random.choice(POST_TEMPLATES).format(topic=topic)
                group = random.choice(eligible_groups)
                image_file = self._build_image_file(topic, image_cache)

                post = CommunityPost.objects.create(
                    user=user,
                    group=group,
                    content=content,
                    audience_gender=gender,
                    is_anonymous=False,
                    image=image_file,
                    video=None,
                )
                post.groups.add(group)
                total_posts += 1

        return total_posts

    def _create_statuses(self, users, groups, statuses_per_user, image_cache):
        if statuses_per_user <= 0:
            return 0

        groups_by_gender = {
            "female": [g for g in groups if g.audience_gender == "female"],
            "male": [g for g in groups if g.audience_gender == "male"],
        }

        total_statuses = 0
        for user in users:
            gender = getattr(getattr(user, "ai_persona", None), "gender", None) or "female"
            eligible_groups = groups_by_gender.get(gender) or groups

            for idx in range(statuses_per_user):
                topic = HEALTH_TOPICS[(idx + random.randint(0, 999)) % len(HEALTH_TOPICS)]
                status_text = f"Quick update on {topic}. Keep your routine healthy."[:250]
                image_file = self._build_image_file(topic, image_cache)

                CommunityStatus.objects.create(
                    user=user,
                    group=random.choice(eligible_groups) if eligible_groups else None,
                    audience_gender=gender,
                    content=status_text,
                    image=image_file,
                )
                total_statuses += 1

        return total_statuses

    def _build_image_file(self, topic, image_cache):
        key = topic.strip().lower()
        if key not in image_cache:
            if self.image_source == "online":
                image_cache[key] = self._download_topic_image_bytes(topic)
            else:
                image_cache[key] = self._svg_topic_image_bytes(topic)

        image_bytes = image_cache[key]
        if not image_bytes:
            image_bytes = self._svg_topic_image_bytes("health awareness")

        slug = key.replace(" ", "-")[:35]
        extension = "png" if self.image_source == "online" else "svg"
        return ContentFile(image_bytes, name=f"{slug}-{random.randint(1000, 9999)}.{extension}")

    def _svg_topic_image_bytes(self, topic):
        safe_text = escape((topic or "health awareness")[:60])
        svg = f"""<svg xmlns='http://www.w3.org/2000/svg' width='1080' height='1080' viewBox='0 0 1080 1080'>
<defs>
  <linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>
    <stop offset='0%' stop-color='#0ea5e9'/>
    <stop offset='100%' stop-color='#22c55e'/>
  </linearGradient>
</defs>
<rect width='1080' height='1080' fill='url(#g)'/>
<circle cx='900' cy='180' r='150' fill='rgba(255,255,255,0.18)'/>
<circle cx='160' cy='900' r='220' fill='rgba(255,255,255,0.14)'/>
<text x='540' y='500' text-anchor='middle' fill='white' font-family='Arial, sans-serif' font-size='74' font-weight='700'>Health Topic</text>
<text x='540' y='605' text-anchor='middle' fill='white' font-family='Arial, sans-serif' font-size='56' font-weight='600'>{safe_text}</text>
</svg>"""
        return svg.encode("utf-8")

    def _download_topic_image_bytes(self, topic):
        topic_text = quote_plus(topic)
        urls = [
            f"https://placehold.co/1080x1080/png?text={topic_text}",
            f"https://dummyimage.com/1080x1080/edf2f7/1f2937.png&text={topic_text}",
        ]

        for url in urls:
            try:
                request = Request(url, headers={"User-Agent": "Mozilla/5.0 (AfyaTestSeeder)"})
                with urlopen(request, timeout=self.online_timeout) as response:
                    return response.read()
            except Exception:
                continue

        # fallback to fast local SVG to avoid slow or failed network runs
        return self._svg_topic_image_bytes(topic)
