# utils.py
import csv
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from .models import Program

def generate_weekly_program_schedule_csv():
    programs = Program.objects.all()
    
    csv_file = BytesIO()
    writer = csv.writer(csv_file)
    writer.writerow(['Time', 'Program Name', 'Status', 'Date', 'Is New'])
    
    for program in programs:
        writer.writerow([program.time_and_date, program.program_name, program.status, program.date, program.is_new])
    
    csv_file.seek(0)
    return csv_file

def generate_weekly_program_schedule_pdf():
    programs = Program.objects.all()
    
    pdf_file = BytesIO()
    p = canvas.Canvas(pdf_file, pagesize=letter)
    width, height = letter
    
    p.drawString(100, height - 100, "Weekly Program Schedule")
    p.drawString(100, height - 120, "Time - Program Name - Status - Date - Is New")
    
    y = height - 140
    for program in programs:
        line = f"{program.time_and_date} - {program.program_name} - {program.status} - {program.date} - {program.is_new}"
        p.drawString(100, y, line)
        y -= 20
    
    p.showPage()
    p.save()
    
    pdf_file.seek(0)
    return pdf_file
