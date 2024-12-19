from django.db import models
from autoslug import AutoSlugField
from PIL import Image
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.utils import timezone


def equipment_image_upload_path(instance, filename):
    # Customize upload path based on instance attributes
    return f'media/{filename}'


def generate_slug(instance):
    return f'{instance.name}-{instance.serial_number}'


class Equipment(models.Model):
    CATEGORY_CHOICES = [
        ('Audio', 'Audio'),
        ('Lighting', 'Lighting'),
        ('Power', 'Power'),
        ('Video', 'Video'),
        ('Other', 'Other'),
    ]

    TYPE_MODEL_CHOICES = [
        ('Tronic', 'Tronic'),
        ('Sony', 'Sony'),
        ('USB Capture', 'USB Capture'),
        ('N/A', 'N/A'),
    ]
    
    STATUS_CHOICES = [
        ('Available', 'Available'),
        ('Reserved', 'Reserved'),
        ('In Maintenance', 'In Maintenance'),
    ]

    name = models.CharField(max_length=255, verbose_name="Equipment Name")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name="Category")
    type_model = models.CharField(max_length=255, choices=TYPE_MODEL_CHOICES, verbose_name="Type/Model")
    serial_number = models.CharField(max_length=100, verbose_name="Serial Number", unique=True)
    
    equipment_image = models.ImageField(upload_to=equipment_image_upload_path, verbose_name="Equipment Image")
    slug = AutoSlugField(populate_from=generate_slug, default='', unique=True, editable=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Available', verbose_name="Status")
    registered_date = models.DateTimeField(default=timezone.now, verbose_name="Registered Date")

    class Meta:
        verbose_name = "Equipment"
        verbose_name_plural = "Equipment"

    def __str__(self):
        return f"{self.name} - {self.category} - {self.status}"


class AssignmentDetail(models.Model):
    detail = models.CharField(max_length=255, verbose_name="Detail")

    def __str__(self):
        return self.detail


class TaskAssignment(models.Model):
    CATEGORY_CHOICES = [
        ('Live', 'Live'),
        ('Recording', 'Recording'),
        ('Other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Under Review', 'Under Review'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Returned', 'Returned'),
    ]

    STAGE_CHOICES = [
        ('Production', 'Production'),
        ('Technical', 'Technical'),
        ('Treasurer', 'Treasurer'),
        ('Cashier', 'Cashier'),
    ]

    assignment = models.CharField(max_length=255, verbose_name="Assignment")
    date = models.DateField(verbose_name="Date")
    location = models.CharField(max_length=255, verbose_name="Location of the Assignment")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name="Category")
    details = models.ManyToManyField('AssignmentDetail', verbose_name="Details of the Assignment")
    submission_date = models.DateField(verbose_name="Date of Submission", null=True, blank=True)
    persons_assigned = models.ManyToManyField(User, verbose_name="Person(s) Assigned", related_name='assigned_tasks')
    agreement = models.BooleanField(default=False, verbose_name="Agreement")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')

    slug = models.SlugField(default="", null=False)
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, default=1, related_name='requested_tasks')
    rejection_reason = models.TextField(blank=True)
    current_stage = models.CharField(max_length=20, choices=STAGE_CHOICES, default='Production')

    production_approved = models.BooleanField(default=False)
    technical_manager_approved = models.BooleanField(default=False)
    technical_approved = models.BooleanField(default=False)
    treasurer_approved = models.BooleanField(default=False)
    cashier_approved = models.BooleanField(default=False)
    assistant_treasurer_approved = models.BooleanField(default=False)

    production_approver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='production_approved_tasks')
    technical_manager_approver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='technical_manager_approved_tasks')
    technical_approver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='technical_approved_tasks')
    treasurer_approver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='treasurer_approved_tasks')
    assistant_treasurer_approver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assistant_treasurer_approved_tasks')
    cashier_approver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='cashier_approved_tasks')

    # New fields for return confirmation
    return_confirmed = models.BooleanField(default=False, verbose_name="Return Confirmed")
    return_date = models.DateTimeField(null=True, blank=True, verbose_name="Return Date")
    return_confirmed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='confirmed_returns', verbose_name="Return Confirmed By")

    def confirm_return(self, user):
        """Mark the return as confirmed and update equipment status."""
        self.return_confirmed = True
        self.return_date = timezone.now()
        self.return_confirmed_by = user

        # Ensure the task is saved after confirming return
        self.save()

        # Update the status of all related equipment to 'Available'
        for assignment_equipment in self.assigned_equipments.all():
            assignment_equipment.equipment.status = 'Available'
            assignment_equipment.equipment.save()

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.assignment)

        # Automatically archive task if it's approved
        if self.status == 'Approved':
            self.archive_approved_task()

        super(TaskAssignment, self).save(*args, **kwargs)

    def archive_approved_task(self):
        """Archives the approved task assignment."""
        approvers = []

        # Check each approver safely
        if self.production_approved and self.production_approver:
            approvers.append({'name': self.production_approver.get_full_name(), 'role': 'Production Manager'})
        
        if self.technical_manager_approved and self.technical_manager_approver:
            approvers.append({'name': self.technical_manager_approver.get_full_name(), 'role': 'Technical Manager'})
        
        if self.technical_approved and self.technical_approver:
            approvers.append({'name': self.technical_approver.get_full_name(), 'role': 'Technical'})
        
        if self.treasurer_approved and self.treasurer_approver:
            approvers.append({'name': self.treasurer_approver.get_full_name(), 'role': 'Treasurer'})
        
        if self.assistant_treasurer_approved and self.assistant_treasurer_approver:
            approvers.append({'name': self.assistant_treasurer_approver.get_full_name(), 'role': 'Assistant Treasurer'})
        
        if self.cashier_approved and self.cashier_approver:
            approvers.append({'name': self.cashier_approver.get_full_name(), 'role': 'Cashier'})

        # Create archive
        TaskAssignmentArchive.objects.create(
            original_task_assignment_id=self,
            requested_by=self.requested_by,
            category=self.category,
            persons_assigned=list(self.persons_assigned.values('id', 'username')),  # Serialize the persons assigned
            submission_date=self.submission_date,
            equipment_details=list(self.details.values('id', 'detail')),  # Serialize correct field from AssignmentDetail model
            status='Approved',
            approved_by=approvers,  # JSON list of approvers
            approval_date=timezone.now(),
            reason='Request Approved'
        )

    def __str__(self):
        return self.assignment


class AssignmentEquipment(models.Model):
    task_assignment = models.ForeignKey(TaskAssignment, on_delete=models.CASCADE)
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.equipment.name} - Quantity: {self.quantity}"


class TaskAssignmentArchive(models.Model):
    original_task_assignment_id = models.ForeignKey('TaskAssignment', on_delete=models.CASCADE)
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.CharField(max_length=255)
    persons_assigned = models.JSONField()  # or models.TextField() if not using JSONField
    submission_date = models.DateTimeField()
    equipment_details = models.JSONField()  # or models.TextField() if not using JSONField
    status = models.CharField(max_length=50)
    approved_by = models.JSONField()  # e.g., [{'name': 'John Doe', 'role': 'Treasurer'}]
    approval_date = models.DateTimeField(null=True, blank=True)
    reason = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Archived Task: {self.original_task_assignment_id.assignment}"
