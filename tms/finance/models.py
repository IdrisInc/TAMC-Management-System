from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver

class FinancialRequest(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Under Review', 'Under Review'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    amount_numeric = models.DecimalField(max_digits=10, decimal_places=2)
    amount_words = models.CharField(max_length=255)
    purpose = models.CharField(max_length=255)
    description = models.CharField(max_length=255, default='No description provided')
    total_request = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    wef = models.DateField(blank=True, null=True)
    account_to_charge = models.CharField(max_length=100, blank=True, null=True)
    account_code = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    
    # New field to track the approval date
    date_approved = models.DateField(blank=True, null=True)
        # New field to store rejection comments
    rejection_comment = models.TextField(blank=True, null=True)

    # Approval fields
    approved_by_production = models.ManyToManyField(User, related_name='approved_by_production', blank=True)
    approved_by_technical_manager = models.ManyToManyField(User, related_name='approved_by_technical_manager', blank=True)
    approved_by_finance = models.ManyToManyField(User, related_name='approved_by_finance', blank=True)
    approved_by_treasurer = models.ManyToManyField(User, related_name='approved_by_treasurer', blank=True)
    approved_by_cashier = models.ManyToManyField(User, related_name='approved_by_cashier', blank=True)
    approved_by_assistant_treasurer = models.ManyToManyField(User, related_name='approved_by_assistant_treasurer', blank=True)

    def update_status(self):
        # If Cashier has approved, set status to 'Approved' regardless of other roles
        if self.approved_by_cashier.exists():
            self.status = 'Approved'
            self.date_approved = timezone.now()  # Set the approval date
        # If any role except Cashier has approved, set status to 'Under Review'
        elif (self.approved_by_production.exists() or 
              self.approved_by_technical_manager.exists() or 
              self.approved_by_finance.exists() or 
              self.approved_by_assistant_treasurer.exists() or
              self.approved_by_treasurer.exists()):
            self.status = 'Under Review'
            self.date_approved = None  # Reset approval date if under review
        # If no approvals exist, set status to 'Pending'
        else:
            self.status = 'Pending'
            self.date_approved = None  # Reset approval date if pending
        
        # Save the status update
        self.save(update_fields=['status', 'date_approved'])

    def calculate_total_request(self):
        self.total_request = sum(item.total_request for item in self.items.all())

    def save(self, *args, **kwargs):
        initial_save = not self.pk
        if initial_save:
            super().save(*args, **kwargs)  # Save initially to get a primary key
        if not kwargs.pop('skip_total_request', False):
            self.calculate_total_request()
        if not initial_save:
            super().save(*args, **kwargs)  # Save again to update total_request

    class Meta:
        ordering = ['-created_at']


class Item(models.Model):
    financial_request = models.ForeignKey(FinancialRequest, on_delete=models.CASCADE, related_name='items')
    item_name = models.CharField(max_length=255, default='My Item')
    quantity = models.IntegerField(blank=False)
    price = models.DecimalField(max_digits=15, decimal_places=2, blank=False)
    total_request = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    def save(self, *args, **kwargs):
        self.total_request = self.quantity * self.price
        super().save(*args, **kwargs)

    def __str__(self):
        return self.item_name


class FinancialRequestArchive(models.Model):
    original_request = models.ForeignKey(FinancialRequest, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount_numeric = models.DecimalField(max_digits=10, decimal_places=2)
    amount_words = models.CharField(max_length=255)
    purpose = models.CharField(max_length=255)
    description = models.CharField(max_length=255, default='No description provided')
    total_request = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    wef = models.DateField(blank=True, null=True)
    account_to_charge = models.CharField(max_length=100, blank=True, null=True)
    account_code = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=FinancialRequest.STATUS_CHOICES, default='Pending')
    date_approved = models.DateField(blank=True, null=True)
    archived_at = models.DateTimeField(auto_now_add=True)

    # Fields to store the names of users who approved the request
    approved_by_production = models.TextField(blank=True, null=True)
    approved_by_technical_manager = models.TextField(blank=True, null=True)
    approved_by_finance = models.TextField(blank=True, null=True)
    approved_by_treasurer = models.TextField(blank=True, null=True)
    approved_by_cashier = models.TextField(blank=True, null=True)
    approved_by_assistant_treasurer = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-archived_at']


@receiver(post_save, sender=FinancialRequest)
def archive_financial_request(sender, instance, created, **kwargs):
    if instance.status == 'Approved' and not created:
        if not FinancialRequestArchive.objects.filter(original_request=instance).exists():
            FinancialRequestArchive.objects.create(
                original_request=instance,
                user=instance.user,
                amount_numeric=instance.amount_numeric,
                amount_words=instance.amount_words,
                purpose=instance.purpose,
                description=instance.description,
                total_request=instance.total_request,
                wef=instance.wef,
                account_to_charge=instance.account_to_charge,
                account_code=instance.account_code,
                created_at=instance.created_at,
                status=instance.status,
                date_approved=instance.date_approved,
                approved_by_production=', '.join([u.username for u in instance.approved_by_production.all()]),
                approved_by_technical_manager=', '.join([u.username for u in instance.approved_by_technical_manager.all()]),
                approved_by_finance=', '.join([u.username for u in instance.approved_by_finance.all()]),
                approved_by_treasurer=', '.join([u.username for u in instance.approved_by_treasurer.all()]),
                approved_by_cashier=', '.join([u.username for u in instance.approved_by_cashier.all()]),
                approved_by_assistant_treasurer=', '.join([u.username for u in instance.approved_by_assistant_treasurer.all()]),
            )



@receiver(post_save, sender=Item)
@receiver(post_delete, sender=Item)
def update_financial_request_total(sender, instance, **kwargs):
    instance.financial_request.calculate_total_request()
    instance.financial_request.save(skip_total_request=True)
