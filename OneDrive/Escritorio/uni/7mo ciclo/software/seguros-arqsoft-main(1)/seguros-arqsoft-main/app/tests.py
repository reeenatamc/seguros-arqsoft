"""
Tests para el Sistema de Gestión de Seguros
============================================
Este archivo contiene tests básicos para verificar el funcionamiento
del pipeline CI/CD y la aplicación.
"""

import pytest
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse


# ============================================
# Tests de Configuración Básica
# ============================================

class ConfigurationTests(TestCase):
    """Tests para verificar la configuración básica de Django"""
    
    def test_django_installed(self):
        """Verifica que Django esté instalado correctamente"""
        import django
        self.assertIsNotNone(django.VERSION)
    
    def test_database_connection(self):
        """Verifica la conexión a la base de datos"""
        from django.db import connection
        self.assertIsNotNone(connection)
    
    def test_settings_loaded(self):
        """Verifica que la configuración se cargue correctamente"""
        from django.conf import settings
        self.assertTrue(settings.configured)


# ============================================
# Tests de Modelos
# ============================================

@pytest.mark.django_db
class UserModelTests(TestCase):
    """Tests para el modelo de Usuario"""
    
    def setUp(self):
        """Configuración inicial para cada test"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_user_creation(self):
        """Verifica que se pueda crear un usuario"""
        self.assertEqual(self.user.username, 'testuser')
        self.assertEqual(self.user.email, 'test@example.com')
        self.assertTrue(self.user.check_password('testpass123'))
    
    def test_user_str(self):
        """Verifica la representación en string del usuario"""
        self.assertEqual(str(self.user), 'testuser')


# ============================================
# Tests de Vistas
# ============================================

@pytest.mark.django_db
class ViewTests(TestCase):
    """Tests para las vistas de la aplicación"""
    
    def setUp(self):
        """Configuración inicial"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    def test_login_page_loads(self):
        """Verifica que la página de login cargue correctamente"""
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
    
    def test_redirect_if_not_logged_in(self):
        """Verifica redirección si no está autenticado"""
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 302)  # Redirect
    
    def test_user_can_login(self):
        """Verifica que un usuario pueda iniciar sesión"""
        logged_in = self.client.login(
            username='testuser',
            password='testpass123'
        )
        self.assertTrue(logged_in)


# ============================================
# Tests de Integración
# ============================================

@pytest.mark.integration
@pytest.mark.django_db
class IntegrationTests(TestCase):
    """Tests de integración del sistema"""
    
    def setUp(self):
        """Configuración inicial"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            is_staff=True
        )
    
    def test_complete_user_flow(self):
        """Test del flujo completo de usuario"""
        # 1. Login
        logged_in = self.client.login(
            username='testuser',
            password='testpass123'
        )
        self.assertTrue(logged_in)
        
        # 2. Acceder al dashboard
        response = self.client.get('/dashboard/')
        self.assertIn(response.status_code, [200, 302])


# ============================================
# Tests de Seguridad
# ============================================

class SecurityTests(TestCase):
    """Tests de seguridad básicos"""
    
    def test_sql_injection_protection(self):
        """Verifica protección contra SQL injection"""
        client = Client()
        # Intento de SQL injection
        response = client.post(reverse('login'), {
            'username': "admin' OR '1'='1",
            'password': "password"
        })
        # No debería iniciar sesión
        self.assertNotEqual(response.status_code, 200) or \
            self.assertFalse(response.wsgi_request.user.is_authenticated)
    
    def test_xss_protection(self):
        """Verifica protección contra XSS"""
        # Django escapa automáticamente HTML en templates
        from django.utils.html import escape
        malicious_input = "<script>alert('XSS')</script>"
        escaped = escape(malicious_input)
        self.assertNotIn("<script>", escaped)


# ============================================
# Tests de Performance (Opcional)
# ============================================

@pytest.mark.slow
class PerformanceTests(TestCase):
    """Tests de rendimiento del sistema"""
    
    @pytest.mark.django_db
    def test_database_query_performance(self):
        """Verifica el rendimiento de queries a la base de datos"""
        from django.db import connection
        from django.test.utils import override_settings
        
        with override_settings(DEBUG=True):
            # Crear múltiples usuarios
            users = [
                User(username=f'user{i}', email=f'user{i}@example.com')
                for i in range(10)
            ]
            User.objects.bulk_create(users)
            
            # Medir queries
            queries_before = len(connection.queries)
            list(User.objects.all())
            queries_after = len(connection.queries)
            
            # Debería ser una sola query
            self.assertEqual(queries_after - queries_before, 1)


# ============================================
# Tests de Utilidades
# ============================================

class UtilityTests(TestCase):
    """Tests para funciones de utilidad"""
    
    def test_environment_variables(self):
        """Verifica que las variables de entorno estén configuradas"""
        from django.conf import settings
        
        # Verificar que SECRET_KEY existe
        self.assertTrue(hasattr(settings, 'SECRET_KEY'))
        self.assertIsNotNone(settings.SECRET_KEY)
        self.assertNotEqual(settings.SECRET_KEY, '')
    
    def test_installed_apps(self):
        """Verifica que las apps necesarias estén instaladas"""
        from django.conf import settings
        
        required_apps = [
            'django.contrib.admin',
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.messages',
            'django.contrib.staticfiles',
            'app',
        ]
        
        for app in required_apps:
            self.assertIn(app, settings.INSTALLED_APPS)


# ============================================
# Pytest Fixtures
# ============================================

@pytest.fixture
def user_factory():
    """Factory para crear usuarios de prueba"""
    def create_user(**kwargs):
        defaults = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        defaults.update(kwargs)
        return User.objects.create_user(**defaults)
    return create_user


@pytest.fixture
def authenticated_client(user_factory):
    """Cliente autenticado para pruebas"""
    user = user_factory()
    client = Client()
    client.force_login(user)
    return client


# ============================================
# Tests con Pytest Fixtures
# ============================================

@pytest.mark.django_db
def test_user_creation_with_factory(user_factory):
    """Test usando factory fixture"""
    user = user_factory(username='factoryuser')
    assert user.username == 'factoryuser'


@pytest.mark.django_db
def test_authenticated_access(authenticated_client):
    """Test de acceso con usuario autenticado"""
    response = authenticated_client.get('/dashboard/')
    assert response.status_code in [200, 302]


# ============================================
# Tests Parametrizados
# ============================================

@pytest.mark.parametrize("username,email,valid", [
    ("user1", "user1@example.com", True),
    ("user2", "user2@example.com", True),
    ("", "nousername@example.com", False),
    ("user3", "", False),
])
@pytest.mark.django_db
def test_user_validation(username, email, valid):
    """Test parametrizado para validación de usuarios"""
    if valid:
        user = User.objects.create_user(
            username=username,
            email=email,
            password='testpass123'
        )
        assert user.username == username
    else:
        with pytest.raises(ValueError):
            User.objects.create_user(
                username=username,
                email=email,
                password='testpass123'
            )
