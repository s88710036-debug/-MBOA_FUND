from django.test import TestCase
from django.utils import timezone
from apps.accounts.models import User, Profile, UserConnection


class UserModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
            role=User.Role.MEMBRE,
        )

    def test_user_creation(self):
        self.assertEqual(self.user.username, "testuser")
        self.assertEqual(self.user.email, "test@example.com")
        self.assertEqual(self.user.role, User.Role.MEMBRE)
        self.assertEqual(self.user.status, User.Status.ACTIF)

    def test_user_str(self):
        expected = "Test User (Membre)"
        self.assertEqual(str(self.user), expected)

    def test_is_tresorier_property(self):
        self.assertFalse(self.user.is_tresorier)
        self.user.role = User.Role.TRESORIER
        self.user.save()
        self.assertTrue(self.user.is_tresorier)

    def test_is_super_admin_property(self):
        self.assertFalse(self.user.is_super_admin)
        self.user.role = User.Role.SUPER_ADMIN
        self.user.save()
        self.assertTrue(self.user.is_super_admin)

    def test_super_admin_is_tresorier(self):
        self.user.role = User.Role.SUPER_ADMIN
        self.user.save()
        self.assertTrue(self.user.is_tresorier)

    def test_user_roles(self):
        self.assertIn(User.Role.SUPER_ADMIN, User.Role.values)
        self.assertIn(User.Role.TRESORIER, User.Role.values)
        self.assertIn(User.Role.MEMBRE, User.Role.values)

    def test_user_statuses(self):
        self.assertIn(User.Status.ACTIF, User.Status.values)
        self.assertIn(User.Status.INACTIF, User.Status.values)
        self.assertIn(User.Status.SUSPENDU, User.Status.values)

    def test_create_super_admin(self):
        admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass123",
            role=User.Role.SUPER_ADMIN,
        )
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.role, User.Role.SUPER_ADMIN)

    def test_create_tresorier(self):
        tresorier = User.objects.create_user(
            username="tresorier",
            email="tresorier@example.com",
            password="trespass123",
            role=User.Role.TRESORIER,
        )
        self.assertTrue(tresorier.is_tresorier)
        self.assertFalse(tresorier.is_super_admin)


class ProfileModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="profileuser",
            email="profile@example.com",
            password="testpass123",
        )
        self.profile = Profile.objects.create(
            user=self.user,
            gender=Profile.Gender.MALE,
            city="Dakar",
            country="Sénégal",
        )

    def test_profile_creation(self):
        self.assertEqual(self.profile.user, self.user)
        self.assertEqual(self.profile.gender, Profile.Gender.MALE)
        self.assertEqual(self.profile.city, "Dakar")
        self.assertEqual(self.profile.country, "Sénégal")

    def test_profile_str(self):
        self.assertEqual(str(self.profile), f"Profil de {self.user.username}")

    def test_profile_gender_choices(self):
        self.assertIn(Profile.Gender.MALE, Profile.Gender.values)
        self.assertIn(Profile.Gender.FEMALE, Profile.Gender.values)
        self.assertIn(Profile.Gender.OTHER, Profile.Gender.values)

    def test_profile_one_to_one_with_user(self):
        with self.assertRaises(Exception):
            Profile.objects.create(
                user=self.user,
                gender=Profile.Gender.FEMALE,
            )

    def test_profile_default_country(self):
        user2 = User.objects.create_user(
            username="user2",
            email="user2@example.com",
            password="testpass123",
        )
        profile2 = Profile.objects.create(user=user2)
        self.assertEqual(profile2.country, "Sénégal")


class UserConnectionModelTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username="user1", email="user1@example.com", password="testpass123"
        )
        self.user2 = User.objects.create_user(
            username="user2", email="user2@example.com", password="testpass123"
        )

    def test_connection_creation(self):
        connection = UserConnection.objects.create(
            from_user=self.user1,
            to_user=self.user2,
            status=UserConnection.ConnectionType.PENDING,
        )
        self.assertEqual(connection.status, UserConnection.ConnectionType.PENDING)

    def test_connection_str(self):
        connection = UserConnection.objects.create(
            from_user=self.user1,
            to_user=self.user2,
        )
        expected = f"{self.user1} -> {self.user2} (En attente)"
        self.assertEqual(str(connection), expected)

    def test_connection_unique_together(self):
        UserConnection.objects.create(from_user=self.user1, to_user=self.user2)
        with self.assertRaises(Exception):
            UserConnection.objects.create(from_user=self.user1, to_user=self.user2)

    def test_connection_status_choices(self):
        self.assertIn(
            UserConnection.ConnectionType.PENDING, UserConnection.ConnectionType.values
        )
        self.assertIn(
            UserConnection.ConnectionType.ACCEPTED, UserConnection.ConnectionType.values
        )
        self.assertIn(
            UserConnection.ConnectionType.REJECTED, UserConnection.ConnectionType.values
        )

    def test_accept_connection(self):
        connection = UserConnection.objects.create(
            from_user=self.user1,
            to_user=self.user2,
        )
        connection.status = UserConnection.ConnectionType.ACCEPTED
        connection.save()
        self.assertEqual(connection.status, UserConnection.ConnectionType.ACCEPTED)
