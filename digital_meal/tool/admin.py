from django.contrib import admin

from .models import Classroom, User, Teacher, BaseModule, SubModule


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['email', 'date_joined', 'last_login', 'is_superuser']


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ['user', 'name', 'first_name', 'canton', 'school_name']


@admin.register(BaseModule)
class BaseModuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'date_created', 'id', 'active',
                    'ddm_path', 'ddm_project_id']
    fields = (
        'name',
        'materials_text',
        'ddm_path',
        'ddm_project_id',
        'report_prefix',
        'active',
        'test_class_url_id'
    )


@admin.register(SubModule)
class SubModuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'url_parameter', 'active']
    fields = (
        'base_module',
        'name',
        'description',
        'materials_text',
        'url_parameter',
        'active'
    )


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'url_id', 'date_created', 'owner', 'base_module',
        'n_started', 'n_finished', 'completion_rate', 'last_started',
        'last_completed', 'is_active'
    ]
    list_filter = ['base_module', 'owner', 'date_created']

    def _get_cached_stats(self, obj):
        """ Cache stats on the object to avoid multiple calls. """
        if not hasattr(obj, '_cached_participation_stats'):
            obj._cached_participation_stats = obj.get_participation_stats()
        return obj._cached_participation_stats

    def n_started(self, obj):
        stats = self._get_cached_stats(obj)
        return stats['n_started']
    n_started.short_description = 'Started Participations'

    def n_finished(self, obj):
        stats = self._get_cached_stats(obj)
        return stats['n_finished']
    n_finished.short_description = 'Finished Participation'

    def completion_rate(self, obj):
        stats = self._get_cached_stats(obj)
        return stats['completion_rate']
    completion_rate.short_description = 'Completion Rate'

    def last_started(self, obj):
        stats = self._get_cached_stats(obj)
        return stats['last_started']
    last_started.short_description = 'Last Participation'

    def last_completed(self, obj):
        stats = self._get_cached_stats(obj)
        return stats['last_completed']
    last_completed.short_description = 'Last Participation'
