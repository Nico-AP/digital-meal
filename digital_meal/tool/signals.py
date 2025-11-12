from django.core.mail import mail_admins
from django.db.models.signals import post_save
from django.dispatch import receiver

from digital_meal.tool.models import Teacher, Classroom


@receiver(post_save, sender=Teacher)
def notify_admins_teacher_created(sender, instance, created, **kwargs):
    """Send email to admins when a new Teacher is created."""
    if created:
        subject = f'New Teacher Created: {instance.first_name} {instance.name}'
        message = f"""
        A new Teacher has been created:
        
        Name: {instance.first_name} {instance.name}
        Canton: {instance.get_canton_display()}
        School: {instance.school_name or 'Not specified'}
        Email: {instance.user.email}
        Date Created: {instance.date_created.strftime('%Y-%m-%d %H:%M:%S')}
        """
        mail_admins(
            subject=subject,
            message=message,
            fail_silently=False,
        )


@receiver(post_save, sender=Classroom)
def notify_admins_classroom_created(sender, instance, created, **kwargs):
    """Send email to admins when a new Classroom is created."""
    if created:
        subject = f'New Classroom Created: {instance.name}'
        message = f"""
        A new Classroom has been created:
        
        Classroom Name: {instance.name}
        URL ID: {instance.url_id}
        Owner: {instance.owner.email}
        School Level: {instance.get_school_level_display()}
        School Year: {instance.school_year}
        Subject: {instance.get_subject_display()}
        Instruction Format: {instance.get_instruction_format_display()}
        Base Module: {instance.base_module.name if instance.base_module else 'Not assigned'}
        Date Created: {instance.date_created.strftime('%Y-%m-%d %H:%M:%S')}
        Expiry Date: {instance.expiry_date.strftime('%Y-%m-%d %H:%M:%S')}
        """
        mail_admins(
            subject=subject,
            message=message,
            fail_silently=False,
        )
