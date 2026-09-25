from django.db import models

# Create your models here.

class Doctor(models.Model):
    name = models.CharField(max_length=100)
    speciality = models.CharField(max_length=100)
    bio = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Appointment(models.Model):
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.PROTECT,
        related_name='slots'
    )
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['date', 'start_time']
        constraints = [
            models.UniqueConstraint(
                fields=['doctor', 'date', 'start_time'],
                name='unique_doctor_slot_start',
            ),
            models.CheckConstraint(
                condition=models.Q(
                    end_time__gt=models.F('start_time')
                ),
                name='slot_end_after_start',
            ),
        ]

    def __str__(self):
        return (
            f"{self.doctor.name} - {self.date} | "
            f"{self.start_time} - {self.end_time}")
