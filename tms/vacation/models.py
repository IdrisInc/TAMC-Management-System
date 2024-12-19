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
    custom_holiday_type = models.ForeignKey('HolidayType', on_delete=models.SET_NULL, null=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    my_last_holiday_start = models.DateField()
    my_last_holiday_end = models.DateField()
    current_address = models.TextField()
    delegatee = models.ForeignKey(User, related_name='holiday_delegatee', on_delete=models.CASCADE)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    my_tasks = models.TextField(blank=True, null=True, help_text="Comma-separated list of tasks")
    approved_by = models.ForeignKey(User, related_name='holiday_approved_by', null=True, blank=True, on_delete=models.SET_NULL)
    rejected_by = models.ForeignKey(User, related_name='holiday_rejected_by', null=True, blank=True, on_delete=models.SET_NULL)
    assigned_by = models.ForeignKey(User, related_name='holiday_assigned_by', null=True, blank=True, on_delete=models.SET_NULL)
    
    delegatee_approved = models.BooleanField(default=False)
    production_approved = models.BooleanField(default=False)
    technical_manager_approved = models.BooleanField(default=False)
    treasurer_approved = models.BooleanField(default=False)
    assistant_treasurer_approved = models.BooleanField(default=False)
    marketing_officer_approved = models.BooleanField(default=False)
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
        """Check if the holiday request has received all necessary approvals based on the user's group."""

        if self.user.groups.filter(name='Radio / TV Presenter').exists():
            # Presenter requires Production and Director approvals
            return self.production_approved and self.director_approved

        elif self.user.groups.filter(name='Technical').exists():
            # Technical requires Technical Manager and Director approvals
            return self.technical_manager_approved and self.director_approved

        elif self.user.groups.filter(name__in=['Accountant', 'Cashier']).exists():
            # Cashier or Accountant requires approval from either Treasurer or Assistant Treasurer and Director
            return (self.treasurer_approved or self.assistant_treasurer_approved) and self.director_approved

        elif self.user.groups.filter(name__in=['Cook', 'Driver', 'Cleaner']).exists():
            # Cook, Driver, Cleaner require Marketing Officer and Director approvals
            return self.marketing_officer_approved and self.director_approved

        elif self.user.groups.filter(name__in=['Production Manager', 'Technical Manager', 'Treasurer', 'Assistant Treasurer']).exists():
            # Managers only require Director approval
            return self.director_approved

        return False
    
class ProgramCount(models.Model):
    program_name = models.CharField("Program Name", max_length=255)
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
    duties = models.CharField(max_length=500,default='Not Specified')  # Changed to CharField for comma-separated values
    delegatee = models.ForeignKey(User, related_name='delegatee', on_delete=models.SET_NULL, null=True, blank=True)
    reporting_date = models.DateField()
    # duties = models.ManyToManyField('Duty')  # Assuming you have a Duty model
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    request_date = models.DateField(auto_now_add=True)
    approved_by_delegatee = models.BooleanField(default=False)
    approved_by_production = models.BooleanField(default=False)
    approved_by_technical_manager = models.BooleanField(default=False)
    approved_by_treasurer = models.BooleanField(default=False)
    approved_by_assistant_treasurer = models.BooleanField(default=False)
    approved_by_director = models.BooleanField(default=False)
    
    def get_duties_list(self):
        """Return duties as a list of strings."""
        return self.duties.split(',')

    def set_duties(self, duties_list):
        """Set duties from a list of strings."""
        self.duties = ','.join(duties_list)
    
        # In your PermissionRequest model
    def finalize_approval_by_director(self):
        """Set the approval status by the Director."""
        self.approved_by_director = True
        self.status = 'Approved'
        self.save(update_fields=['approved_by_director', 'status'])

    def is_ready_for_director(self):
        """Check if all prior approvals are done based on delegatee's role."""
        if self.delegatee:
            if self.delegatee.groups.filter(name='Radio / TV Presenter').exists() and self.approved_by_production:
                return True
            elif self.delegatee.groups.filter(name='Technical').exists() and self.approved_by_technical_manager:
                return True
            elif self.delegatee.groups.filter(name__in=['Cashier', 'Accountant']).exists() and self.approved_by_treasurer or self.approved_by_assistant_treasurer:
                return True
            # Check if delegatee approval is required for status to go to 'Under Review'
            elif self.approved_by_delegatee:
                return True
        return False

    def save(self, *args, **kwargs):
        """Manage status transitions based on approval checks."""
        if not self.approved_by_director:  # Only change status if Director hasn't approved it
            if self.is_ready_for_director():
                self.status = 'Under Review'
            else:
                self.status = 'Pending'
        else:
            # When the director has approved, ensure status is set to Approved
            self.status = 'Approved'
        super().save(*args, **kwargs)
        
    def can_be_seen_by(self, user):
        if user.groups.filter(name='Production Manager').exists():
            return self.approved_by_production or self.approved_by_director
        if user.groups.filter(name='Technical Manager').exists():
            return self.approved_by_technical_manager or self.approved_by_director
        if user.groups.filter(name='Treasurer').exists():
            return self.approved_by_treasurer or self.approved_by_director
        if user.groups.filter(name='Assistant Treasurer').exists():
            return self.approved_by_assistant_treasurer or self.approved_by_director
        if user == self.delegatee:
            return self.approved_by_delegatee or self.approved_by_director
        return False