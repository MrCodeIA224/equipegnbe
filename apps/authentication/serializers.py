from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import get_user_model
from .models import User, LivreurProfile, CoursierProfile


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """JWT enrichi avec les infos utilisateur. Accepte email OU username."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        token['username'] = user.username
        token['full_name'] = user.get_full_name()
        return token

    def validate(self, attrs):
        # simplejwt cherche par USERNAME_FIELD (username) directement.
        # Si la valeur ressemble à un email, on la traduit en username.
        login_value = attrs.get(self.username_field, '')
        if '@' in login_value:
            try:
                user_obj = User.objects.get(email=login_value)
                attrs[self.username_field] = user_obj.username
            except User.DoesNotExist:
                pass  # laisse simplejwt lever l'erreur standard

        data = super().validate(attrs)
        user = self.user
        data['user'] = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'full_name': user.get_full_name(),
            'role': user.role,
            'phone': user.phone,
            'city': user.city,
            'is_verified': user.is_verified,
            'profile_picture': user.profile_picture.url if user.profile_picture else None,
        }
        return data


class LivreurProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = LivreurProfile
        fields = ['vehicle_type', 'license_number', 'total_deliveries', 'rating', 'zone']
        read_only_fields = ['total_deliveries', 'rating']


class CoursierProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoursierProfile
        fields = ['preferred_markets', 'total_missions', 'rating', 'zone']
        read_only_fields = ['total_missions', 'rating']


class UserSerializer(serializers.ModelSerializer):
    livreur_profile = LivreurProfileSerializer(read_only=True)
    coursier_profile = CoursierProfileSerializer(read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'phone', 'city', 'address', 'bio',
            'profile_picture', 'is_verified', 'is_available',
            'is_active', 'created_at', 'livreur_profile', 'coursier_profile'
        ]
        read_only_fields = ['is_verified', 'created_at']

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class UserPublicSerializer(serializers.ModelSerializer):
    """Version publique - infos non sensibles"""
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'full_name', 'role', 'city', 'bio', 'profile_picture', 'is_available']

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, label='Confirmer le mot de passe')

    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name',
            'password', 'password2', 'role', 'phone', 'city', 'address'
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({'password': 'Les mots de passe ne correspondent pas.'})
        # Les rôles ADMIN ne peuvent pas s'auto-enregistrer
        if attrs.get('role') == 'ADMIN':
            raise serializers.ValidationError({'role': 'Ce rôle n\'est pas autorisé à l\'inscription.'})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()

        # Créer les profils étendus selon le rôle
        if user.role == 'LIVREUR':
            LivreurProfile.objects.create(user=user)
        elif user.role == 'COURSIER':
            CoursierProfile.objects.create(user=user)

        return user


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Mot de passe actuel incorrect.')
        return value


class AdminUserSerializer(serializers.ModelSerializer):
    """Sérialiseur admin - peut modifier tous les champs"""
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'phone', 'city', 'address', 'bio',
            'profile_picture', 'is_verified', 'is_available',
            'is_active', 'is_staff', 'created_at', 'updated_at'
        ]

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class LivreurPublicSerializer(serializers.ModelSerializer):
    """Infos livreur visibles pour contacter un livreur (cross-service)"""
    full_name = serializers.SerializerMethodField()
    vehicle_type = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    zone = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'full_name', 'phone', 'city', 'profile_picture',
                  'is_available', 'vehicle_type', 'rating', 'zone']

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username

    def get_vehicle_type(self, obj):
        if hasattr(obj, 'livreur_profile'):
            return obj.livreur_profile.vehicle_type
        return None

    def get_rating(self, obj):
        if hasattr(obj, 'livreur_profile'):
            return str(obj.livreur_profile.rating)
        return '5.00'

    def get_zone(self, obj):
        if hasattr(obj, 'livreur_profile'):
            return obj.livreur_profile.zone
        return obj.city
