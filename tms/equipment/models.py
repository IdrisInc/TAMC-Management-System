from django.db import models
from autoslug import AutoSlugField
from PIL import Image
from django.contrib.auth.models import User
from django.utils.text import slugify

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
        # Add more choices as needed
    ]
    
    STATUS_CHOICES = [
        ('Available', 'Available'),
        ('Reserved', 'Reserved'),
        ('In Maintenance', 'In Maintenance'),
        # Add more status options as needed
    ]


    name = models.CharField(max_length=255, verbose_name="Equipment Name")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name="Category")
    type_model = models.CharField(max_length=255, choices=TYPE_MODEL_CHOICES, verbose_name="Type/Model")
    serial_number = models.CharField(max_length=100, verbose_name="Serial Number", unique=True)
    quantity = models.PositiveIntegerField(verbose_name="Quantity",default=0)
    equipment_image = models.ImageField(upload_to=equipment_image_upload_path, verbose_name="Equipment Image")
    slug = AutoSlugField(populate_from=generate_slug, default='', unique=True, editable=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Available', verbose_name="Status")
   
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
    technical_approved = models.BooleanField(default=False)
    treasurer_approved = models.BooleanField(default=False)
    cashier_approved = models.BooleanField(default=False)
    
    
    production_approver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='production_approved_tasks')
    technical_approver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='technical_approved_tasks')
    treasurer_approver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='treasurer_approved_tasks')
    cashier_approver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='cashier_approved_tasks')



   
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.assignment)
        super(TaskAssignment, self).save(*args, **kwargs)

    def __str__(self):
        return self.assignment


class AssignmentEquipment(models.Model):
    task_assignment = models.ForeignKey(TaskAssignment, on_delete=models.CASCADE)
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.equipment.name} - Quantity: {self.quantity}"


