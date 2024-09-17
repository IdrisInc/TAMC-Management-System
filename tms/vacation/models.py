from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError


class HolidayType(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name
    
    
class Holiday(models.Model):
    HOLIDAY_TYPE_CHOICES = [
        ('year', 'Mwaka'),
        ('maternity', 'Uzazi'),
        ('sick', 'Ugonjwa'),
        ('malipo', 'Bila Malipo')
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('Under Review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ]

    user = models.ForeignKey(User, related_name='holiday_user', on_delete=models.CASCADE)
    address = models.TextField()
    working_holiday = models.CharField(max_length=10, choices=HOLIDAY_TYPE_CHOICES, blank=True, null=True)
    custom_holiday_type = models.ForeignKey(HolidayType, on_delete=models.SET_NULL, null=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    my_last_holiday_start = models.DateField()
    my_last_holiday_end = models.DateField()
    current_address = models.TextField()
    delegatee = models.ForeignKey(User, related_name='holiday_delegatee', on_delete=models.CASCADE)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    approved_by = models.ForeignKey(User, related_name='holiday_approved_by', null=True, blank=True, on_delete=models.SET_NULL)
    rejected_by = models.ForeignKey(User, related_name='holiday_rejected_by', null=True, blank=True, on_delete=models.SET_NULL)
    assigned_by = models.ForeignKey(User, related_name='holiday_assigned_by', null=True, blank=True, on_delete=models.SET_NULL)
    
    delegatee_approved = models.BooleanField(default=False)
    production_approved = models.BooleanField(default=False)
    technical_manager_approved = models.BooleanField(default=False)
    treasurer_approved = models.BooleanField(default=False)
    director_approved = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_holiday_type_display()}"

    def get_holiday_type_display(self):
        if self.custom_holiday_type:
            return self.custom_holiday_type.name
        elif self.working_holiday:
            return dict(self.HOLIDAY_TYPE_CHOICES).get(self.working_holiday, 'Unknown')
        return 'Unknown'


    def is_fully_approved(self):
        if self.user.groups.filter(name='Presenter').exists():
            return self.production_approved and self.director_approved
        elif self.user.groups.filter(name='Technical').exists():
            return self.technical_manager_approved and self.director_approved
        elif self.user.groups.filter(name__in=['Finance', 'Cashier']).exists():
            return self.treasurer_approved and self.director_approved
        elif self.user.groups.filter(name__in=['Production', 'Technical Manager', 'Treasurer']).exists():
            return self.director_approved
        return False

class ProgramCount(models.Model):
    program_name = models.CharField("pro.Program",max_length=255)
    count = models.PositiveIntegerField(default=0)
    holiday = models.ForeignKey(Holiday, on_delete=models.CASCADE, related_name='program_counts')

    class Meta:
        unique_together = ('holiday', 'program_name')
        
    def __str__(self):
        return f"{self.program_name} - {self.count} programs for {self.holiday}"



class OverlayDescription(models.Model):
    description = models.TextField()
    added_by = models.ForeignKey(User, on_delete=models.CASCADE)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Description added by {self.added_by.username} on {self.added_on.strftime('%Y-%m-%d %H:%M:%S')}"


class Overlay(models.Model):
    descriptions = models.ManyToManyField(OverlayDescription)



class Duty(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name
    
class PermissionRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('Under Review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    address = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    place = models.CharField(max_length=255)
    description = models.TextField()
    delegatee = models.ForeignKey(User, related_name='delegatee', on_delete=models.SET_NULL, null=True, blank=True)
    reporting_date = models.DateField()
    duties = models.ManyToManyField('Duty')  # Assuming you have a Duty model
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    request_date = models.DateField(auto_now_add=True)
    approved_by_delegatee = models.BooleanField(default=False)
    approved_by_production = models.BooleanField(default=False)
    approved_by_technical_manager = models.BooleanField(default=False)
    approved_by_treasurer = models.BooleanField(default=False)
    approved_by_director = models.BooleanField(default=False)
    
        # In your PermissionRequest model
    def is_ready_for_director(self):
        # Ensure all necessary roles have approved the request
        if self.delegatee.groups.filter(name='Presenter').exists() and self.approved_by_production:
            return True
        elif self.delegatee.groups.filter(name='Technical').exists() and self.approved_by_technical_manager:
            return True
        elif self.delegatee.groups.filter(name__in=['Cashier', 'Finance']).exists() and self.approved_by_treasurer:
            return True
        return False


   
    def save(self, *args, **kwargs):
        # If all necessary approvals are in place, update the status accordingly
        if self.approved_by_director:
            self.status = 'Approved'
        elif self.is_ready_for_director() and self.status != 'Under Review':
            self.status = 'Under Review'
        elif not self.is_ready_for_director() and self.status == 'pending':
            self.status = 'pending'

        super().save(*args, **kwargs)


    def can_be_seen_by(self, user):
        if user.groups.filter(name='Production').exists():
            return self.approved_by_production or self.approved_by_director
        if user.groups.filter(name='Technical Manager').exists():
            return self.approved_by_technical_manager or self.approved_by_director
        if user.groups.filter(name='Treasurer').exists():
            return self.approved_by_treasurer or self.approved_by_director
        if user == self.delegatee:
            return self.approved_by_delegatee or self.approved_by_director
        return False