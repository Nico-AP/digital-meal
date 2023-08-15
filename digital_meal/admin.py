from django.contrib import admin
from digital_meal.models import Classroom, User, Teacher, Module, Track


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['email', 'date_joined', 'last_login', 'is_superuser']


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ['user', 'name', 'first_name', 'canton', 'school_name']


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'ddm_external_project_id', 'date_created', 'active']


@admin.register(Track)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'module', 'date_created', 'id', 'active']


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    """
    Provides an overview of all Pooled Donation Projects.
    """
    list_display = ['name', 'pool_id', 'date_created', 'owner', 'track']
