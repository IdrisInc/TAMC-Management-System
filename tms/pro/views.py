from django.shortcuts import render, redirect, get_object_or_404
from .models import Program
from django.utils import timezone
from datetime import datetime,time,timedelta
from collections import defaultdict


def program_create(request):
    day_choices = Program.DAY_CHOICES
    if request.method == 'POST':
        selected_day = request.POST.get('selected_day')
        for hour in range(24):
            program_name = request.POST.get(f'{hour}_program_name')
            time_str = request.POST.get(f'{hour}_time')
            time_obj = datetime.strptime(time_str, '%H:%M').time()  # Convert time string to time object
            
            # Ensure the time is timezone-aware
            time_and_date = timezone.make_aware(datetime.combine(timezone.now().date(), time_obj), timezone.get_current_timezone())
            
            is_new = request.POST.get(f'{hour}_is_new')
            
            # Create Program object for the selected day
            Program.objects.create(
                selected_day=selected_day,
                time_and_date=time_and_date,
                program_name=program_name,
                is_new=is_new
            )

        return redirect('pro:program_list')  # Redirect to the program list view after successful creation
    else:
        return render(request, 'programs/pro.html', {'day_choices': day_choices})  # Render the program creation form template







from datetime import time, timedelta
from django.utils import timezone

def program_list(request):
    # Generating a list of time objects from 8:00 to 23:00
    hours = [time(hour) for hour in range(5, 24)]  

    # Days of the week
    days = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']

    # Query programs for each day and order by time
    daily_programs = {day: Program.objects.filter(selected_day=day).order_by('time_and_date') for day in days}
    
    # Update program status based on current time
    current_datetime = timezone.now()
    for day_programs in daily_programs.values():
        for program in day_programs:
            # Check if the program's day has passed
            if program.selected_day < current_datetime.strftime('%A').lower():
                program.status = 'played'
            # Check if it's the program's day and time has passed
            elif program.selected_day == current_datetime.strftime('%A').lower():
                if program.time_and_date.time() < current_datetime.time():
                    program.status = 'played'
                # Check if it's the current program's time
                elif program.time_and_date.time() <= current_datetime.time() < (program.time_and_date + timedelta(minutes=30)).time():
                    program.status = 'running'
                # Check if it's the next program's time
                elif program.time_and_date.time() > current_datetime.time():
                    program.status = 'next'
            # For future days
            else:
                program.status = 'not_played'
            program.save()

    return render(request, 'programs/program_list.html', {'hours': hours, 'daily_programs': daily_programs})



def program_edit(request, program_id):
    program = get_object_or_404(Program, pk=program_id)
    if request.method == 'POST':
        program.program_name = request.POST.get('program_name')
        program.status = request.POST.get('status')
        program.is_new = request.POST.get('is_new')
        program.save()
        return redirect('pro:program_list')
    return render(request, 'programs/program_edit.html', {'program': program}) 