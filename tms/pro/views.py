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









def program_list(request):
    # Generating a list of time objects from 5:00 to 23:00
    hours = [time(hour) for hour in range(5, 24)]  

    # Days of the week
    days = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']

    # Query programs for each day and order by time
    daily_programs = {day: Program.objects.filter(selected_day=day).order_by('time_and_date') for day in days}
    
    # Update program status based on current time and day
    current_datetime = datetime.now()
    current_day = current_datetime.strftime('%A').lower()
    print("Current datetime:", current_datetime)
    print("Current day:", current_day)
    for day_programs in daily_programs.values():
        for program in day_programs:
            program_day = program.selected_day.lower()
            program_time = program.time_and_date.time()
            
            if program_day < current_day or (program_day == current_day and program_time < current_datetime.time()):
                program.status = 'played'  # The day has already passed, mark as 'played'
            elif program_day == current_day and program_time <= current_datetime.time() < (program.time_and_date + timedelta(minutes=30)).time():
                program.status = 'running'  # Change status to 'Running'
            elif program_day == current_day and program_time > current_datetime.time():
                program.status = 'next'
            else:
                program.status = 'not_played'  # The day has not come yet, mark as 'not played'
            program.save()
            print(f"Program: {program.program_name}, Status: {program.status}")

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