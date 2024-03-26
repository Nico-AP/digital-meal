from django.contrib import admin
from .models import Classroom, User, Teacher, MainTrack, SubTrack


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['email', 'date_joined', 'last_login', 'is_superuser']


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ['user', 'name', 'first_name', 'canton', 'school_name']


@admin.register(MainTrack)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'date_created', 'id', 'active',
                    'ddm_path', 'ddm_project_id']


@admin.register(SubTrack)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'url_parameter', 'active']


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    """
    Provides an overview of all Pooled Donation Projects.
    """
    list_display = ['name', 'class_id', 'date_created', 'owner', 'track']
