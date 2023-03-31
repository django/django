#bugTest

from django.test import TestCase
from django.contrib.auth import get_user_model

from rmigrate.models import A, B

User = get_user_model()

class TestModels(TestCase):
    def test_delete_user_with_related_objects(self):
        # Cria um usuário, um objeto A e um objeto B relacionado a A
        user = User.objects.create_user(username='testuser', password='testpassword', email='testuser@example.com')
        a = A.objects.create(user=user)
        b = B.objects.create(a=a)
        
        # Tenta excluir o usuário criado, o que deve gerar um erro se o bug não tiver sido corrigido
        with self.assertRaises(Exception):
            user.delete()
        
        # Verifica se os objetos relacionados ainda existem
        self.assertTrue(User.objects.filter(email=user.email).exists())
        self.assertTrue(A.objects.filter(user=user).exists())
        self.assertTrue(B.objects.filter(a__user=user).exists())
        
        # Corrige o bug
        b.a.user = None
        b.a.save()
        
        # Tenta excluir o usuário criado novamente, que agora deve ser excluído com sucesso
        user.delete()
        
        # Verifica se os objetos relacionados também foram excluídos corretamente
        self.assertFalse(A.objects.filter(user=user).exists())
        self.assertFalse(B.objects.filter(a__user=user).exists())
