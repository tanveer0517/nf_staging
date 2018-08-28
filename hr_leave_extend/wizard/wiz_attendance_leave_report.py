# -*- coding: utf-8 -*-
from openerp import api, models, fields, _, SUPERUSER_ID
from openerp.exceptions import except_orm, Warning
import time
from odoo import exceptions
from odoo.exceptions import ValidationError
from datetime import datetime,timedelta
import calendar
from dateutil.relativedelta import relativedelta
import StringIO
import base64
import xlsxwriter

#wizard object to get leave summary report
class wiz_attendance_leave_report(models.TransientModel):
    _name = 'wiz.attendance.leave.report'
    _description = 'Attendance and Leave Report'

    #adding fields
    date_from = fields.Date('Date From')
    date_to = fields.Date('Date To')
    employee_id = fields.Many2many('hr.employee','employee_attendance_leave','emp_id','leav_id','Employee')
    file_data = fields.Binary('File')
    file_name = fields.Char('File Name')
    hide_field = fields.Boolean('Hide Field')

    #method to print the leave summary report in excel
    @api.multi
    def print_report(self):
        cr=self.env.cr
        for i in self:
            leave=self.env["hr.holidays"]
            total=0
            lop_balance=0
            absent=0
            lop_management=0
            final_lop=0
            total_days=0
            payroll_days=0
            onduty=0
            weekoff=0
            holidays=0
            total_leave=0
            earned=0
            casual=0
            privilege=0
            bereavemt=0
            maternity=0
            paternity=0
            datas=[]
            data={}
            fp = StringIO.StringIO()
            workbook = xlsxwriter.Workbook(fp, {'in_memory': True})
            worksheet = workbook.add_worksheet()
            bold = workbook.add_format({'bold': True})
            heading = workbook.add_format({'bold': True,'font_size':15,'bg_color':'yellow'})
            worksheet.set_row(0, 20, heading)
            worksheet.write(0, 3,'Attendance and Leave Report',heading)
            worksheet.set_column('A:A', 25)
            worksheet.set_column('B:C', 15)
            worksheet.set_column('D:M', 20)
            worksheet.set_column('N:EZ', 12)
            
            if i.employee_id:
                for j in i.employee_id:
                    from_date = i.date_from
                    to_date = i.date_to
                    total_days = ((datetime.strptime(to_date, '%Y-%m-%d') - datetime.strptime(from_date, '%Y-%m-%d')).days)+1
                    join_date=j.join_date
                    if join_date:
                        join_date=(datetime.strptime(join_date,'%Y-%m-%d')).strftime('%d-%m-%Y')
                    data={'employee':j.name_related,'emp_id':j.nf_emp,'doj':join_date or 'NA','designation':j.intrnal_desig,'department':j.sub_dep and j.sub_dep.parent_id and j.sub_dep.parent_id.name or 'NA','division':j.sub_dep and j.sub_dep.name or 'NA','branch':j.branch_id and j.branch_id.name or 'NA','work_location':j.work_location or 'NA','state':j.branch_id and j.branch_id.state_id and j.branch_id.state_id.name or 'NA','work_email':j.work_email,'reporting_head':j.coach_id and j.coach_id.name or 'NA','manager':j.parent_id and j.parent_id.name or 'NA'}
                    
                    flag=1
                    count=0
                    weekoff=0
                    present=0
                    absent=0
                    holidays=0
                    wo=False
                    y=12
                    work_home=0
                    man_present=0
                    while from_date <= to_date:
                        worksheet.write(2, y+2,from_date,bold)
                        y+=3
                        curr_date = datetime.strptime(from_date, '%Y-%m-%d')
                        current_day = calendar.day_name[curr_date.weekday()]
                        rest_day_type = j.sub_dep.c_rest_day_type.c_rest_day_type
                        if rest_day_type:
                            if current_day in rest_day_type:
                                weekoff+=1
                                wo=True
                        else:
                            raise exceptions.ValidationError(_('Week Off for '+j.sub_dep.name+' is not defined in ERP.'))
                        nf_att_rec=self.env['nf.leave.swipe'].sudo().search([('employee_id','=',j.nf_emp),('date','=',from_date)],limit=1)
                        oc_status='NA'
                        if nf_att_rec:
                            oc_status=nf_att_rec.attendance_status
                            if oc_status in ['A','L']:
                                curr_date = curr_date.strftime('%Y-%m-%d')
                                sql_query="SELECT id from hr_holidays where employee_id={} and state in ('confirm','validate') and date_from::date <= '{}' and date_to::date >= '{}' and type='remove'".format(j.id,curr_date,curr_date)
                                cr.execute(sql_query)
                                holi_ids = cr.fetchone()
                                holi_rec = False
                                if holi_ids:
                                   holi_rec=self.env['hr.holidays'].sudo().browse(holi_ids[0]) 
                                if holi_rec:
                                    if holi_rec.holiday_status_id.name=='Earned Leaves':
                                        oc_status='EL'
                                    elif holi_rec.holiday_status_id.name=='Casual / Sick Leave':
                                        oc_status='CL/SL'
                                    elif holi_rec.holiday_status_id.name=='Privilege leave':
                                        oc_status='PL'
                                    elif holi_rec.holiday_status_id.name=='Bereavement Leave':
                                        oc_status='BL'
                                    elif holi_rec.holiday_status_id.name=='Maternity Leave':
                                        oc_status='MT'
                                    elif holi_rec.holiday_status_id.name=='Paternity Leave':
                                        oc_status='PT'
                                else:
                                    if  nf_att_rec.is_present == 'Yes':
                                        oc_status='PR'
                                        man_present+=1
                                    elif nf_att_rec.is_present == 'No':
                                        oc_status='AB/LOP'
                                        if nf_att_rec.absent_day == 0.5:
                                            absent+=nf_att_rec.absent_day
                                            man_present+=nf_att_rec.absent_day
                                        else:
                                            absent+=nf_att_rec.absent_day
                                    elif nf_att_rec.work_from_home:
                                        oc_status='WFH'
                                        work_home+=1
                                    else:
                                        oc_status='AB/LOP'
                                        absent+=1

                            elif oc_status=='P':
                                if nf_att_rec.lop_manager:
                                    oc_status='LOP'
                                    lop_management+=nf_att_rec.lop_day
                                else:
                                    oc_status='PR'

                            elif oc_status=='H':
                                if wo:
                                    oc_status='WO'
                                else:
                                    oc_status=='H'
                                holidays+=1
                                wo=False

                        start_time=datetime.strptime(from_date,'%Y-%m-%d').strftime('%Y-%m-%d 00:00:01')
                        end_time=datetime.strptime(from_date,'%Y-%m-%d').strftime('%Y-%m-%d 23:59:59')
                        att_rec=self.env['nf.biometric'].sudo().search([('emp_id','=',j.nf_emp),('attendance_date','>=',start_time),('attendance_date','<=',end_time)],order='attendance_date asc')
                        intime='NA'
                        outime='NA'
                        if att_rec:
                            intime=att_rec[0].attendance_date.split(' ')[1]
                            outime=att_rec[-1].attendance_date.split(' ')[1]
                        data.update({'intime'+str(flag):intime,'outime'+str(flag):outime,'oc'+str(flag):oc_status})
                        from_date=(datetime.strptime(from_date,'%Y-%m-%d')+relativedelta(days=1)).strftime('%Y-%m-%d')
                        intime='NA'
                        outime='NA'
                        flag+=1
                    total_leave=earned+casual+privilege+bereavemt+maternity+paternity
                    holidays=holidays-weekoff
                    final_lop=absent+lop_management
                    payroll_days=total_days-final_lop
                    present=total_days-final_lop-holidays-weekoff-total_leave+man_present+work_home
                    data.update({'present_days':present,'onduty':onduty,'weekoff':weekoff,'holidays':holidays,'total_leave':total_leave,'lop_balance':lop_balance,'absent':absent,'lop_management':lop_management,'final_lop':final_lop,'total_days':total_days,'payroll_days':payroll_days,'earned':earned,'casual':casual,'privilege':privilege,'bereavemt':bereavemt,'maternity':maternity,'paternity':paternity,'biometric':'NA'})
                    datas.append(data)

                worksheet.write(3, 0,'Employee',bold)
                worksheet.write(3, 1,'Employee ID',bold)
                worksheet.write(3, 2,'Date of Joining',bold)
                worksheet.write(3, 3,'Designation',bold)
                worksheet.write(3, 4,'Department',bold)
                worksheet.write(3, 5,'Division',bold)
                worksheet.write(3, 6,'Branch',bold)
                worksheet.write(3, 7,'Work Location',bold)
                worksheet.write(3, 8,'State',bold)
                worksheet.write(3, 9,'Work Email',bold)
                worksheet.write(3, 10,'Reporting Head',bold)
                worksheet.write(3, 11,'Manager',bold)
                worksheet.write(3, 12,'Biometric Status',bold)
                z=y
                y=12
                while y<z:
                    worksheet.write(3, y+1,'First Punch',bold)
                    worksheet.write(3, y+2,'Last Punch',bold)
                    worksheet.write(3, y+3,'OC',bold)
                    y+=3
                worksheet.write(3, y+1,'Present Days',bold)
                #worksheet.write(3, y+2,'On Duty',bold)
                worksheet.write(3, y+2,'Week Off',bold)
                worksheet.write(3, y+3,'Holidays',bold)
                worksheet.write(3, y+4,'EL',bold)
                worksheet.write(3, y+5,'CL/SL',bold)
                worksheet.write(3, y+6,'MT',bold)
                worksheet.write(3, y+7,'PT',bold)
                worksheet.write(3, y+8,'PL',bold)
                worksheet.write(3, y+9,'BL',bold)
                worksheet.write(3, y+10,'Total Leaves Applied',bold)
                #worksheet.write(3, y+11,'LOP as per Leave Balance',bold)
                worksheet.write(3, y+11,'Absent',bold)
                worksheet.write(3, y+12,'LOP as per Management',bold)
                worksheet.write(3, y+13,'Final LOP',bold)
                worksheet.write(3, y+14,'Total Days',bold)
                worksheet.write(3, y+15,'Payroll Days',bold)

            else:
                emp_obj=self.env['hr.employee']
                emp_ids=emp_obj.sudo().search([('active','=',True)])
                for emp_rec in emp_ids:
                    from_date = i.date_from
                    to_date = i.date_to
                    total_days = ((datetime.strptime(to_date, '%Y-%m-%d') - datetime.strptime(from_date, '%Y-%m-%d')).days)+1
                    join_date=emp_rec.join_date
                    if join_date:
                        join_date=(datetime.strptime(join_date,'%Y-%m-%d')).strftime('%d-%m-%Y')
                    data={'employee':emp_rec.name_related,'emp_id':emp_rec.nf_emp,'doj':join_date or 'NA','designation':emp_rec.intrnal_desig,'department':emp_rec.sub_dep and emp_rec.sub_dep.parent_id and emp_rec.sub_dep.parent_id.name or 'NA','division':emp_rec.sub_dep and emp_rec.sub_dep.name or 'NA','branch':emp_rec.branch_id and emp_rec.branch_id.name or 'NA','work_location':emp_rec.work_location or 'NA','state':emp_rec.branch_id and emp_rec.branch_id.state_id and emp_rec.branch_id.state_id.name or 'NA','work_email':emp_rec.work_email,'reporting_head':emp_rec.coach_id and emp_rec.coach_id.name or 'NA','manager':emp_rec.parent_id and emp_rec.parent_id.name or 'NA'}
                    
                    flag=1
                    count=0
                    weekoff=0
                    present=0
                    absent=0
                    holidays=0
                    wo=False
                    y=12
                    while from_date <= to_date:
                        worksheet.write(2, y+2,from_date,bold)
                        y+=3
                        curr_date = datetime.strptime(from_date, '%Y-%m-%d')
                        current_day = calendar.day_name[curr_date.weekday()]
                        rest_day_type = emp_rec.sub_dep.c_rest_day_type.c_rest_day_type
                        if rest_day_type:
                            if current_day in rest_day_type:
                                weekoff+=1
                                wo=True
                        else:
                            raise exceptions.ValidationError(_('Week Off for '+emp_rec.sub_dep.name+' is not defined in ERP.'))
                        nf_att_rec=self.env['nf.leave.swipe'].sudo().search([('employee_id','=',emp_rec.nf_emp),('date','=',from_date)],limit=1)
                        oc_status='NA'
                        if nf_att_rec:
                            oc_status=nf_att_rec.attendance_status
                            if oc_status in ['A','L']:
                                curr_date = curr_date.strftime('%Y-%m-%d')
                                sql_query="SELECT id from hr_holidays where employee_id={} and state in ('confirm','validate') and date_from::date <= '{}' and date_to::date >= '{}' and type='remove'".format(emp_rec.id,curr_date,curr_date)
                                cr.execute(sql_query)
                                holi_ids = cr.fetchone()
                                holi_rec = False
                                if holi_ids:
                                   holi_rec=self.env['hr.holidays'].sudo().browse(holi_ids[0]) 
                                if holi_rec:
                                    count=holi_rec.number_of_days_temp
                                    if holi_rec.number_of_days_temp > 1:
                                        count=1
                                    else:
                                        count=holi_rec.number_of_days_temp
                                    if holi_rec.holiday_status_id.name=='Earned Leaves':
                                        oc_status='EL'
                                        earned+=count
                                    elif holi_rec.holiday_status_id.name=='Casual / Sick Leave':
                                        oc_status='CL/SL'
                                        casual+=count
                                    elif holi_rec.holiday_status_id.name=='Privilege leave':
                                        oc_status='PL'
                                        privilege+=count
                                    elif holi_rec.holiday_status_id.name=='Bereavement Leave':
                                        oc_status='BL'
                                        bereavemt+=count
                                    elif holi_rec.holiday_status_id.name=='Maternity Leave':
                                        oc_status='MT'
                                        maternity+=count
                                    elif holi_rec.holiday_status_id.name=='Paternity Leave':
                                        oc_status='PT'
                                        paternity+=count
                                else:
                                    if  nf_att_rec.is_present == 'Yes':
                                        oc_status='PR'
                                        present+=1
                                    elif nf_att_rec.is_present == 'No':
                                        oc_status='AB/LOP'
                                        if nf_att_rec.absent_day == 0.5:
                                            absent+=nf_att_rec.absent_day
                                            present+=nf_att_rec.absent_day
                                        else:
                                            absent+=nf_att_rec.absent_day
                                    elif nf_att_rec.work_from_home:
                                        oc_status='WFH'
                                        present+=1
                                    else:
                                        oc_status='AB/LOP'
                                        absent+=1

                            elif oc_status=='P':
                                if nf_att_rec.lop_manager:
                                    oc_status='LOP'
                                    if nf_att_rec.lop_day == 0.5:
                                        lop_management+=nf_att_rec.lop_day
                                        present+=nf_att_rec.lop_day
                                    else:
                                        lop_management+=nf_att_rec.lop_day
                                else:
                                    oc_status='PR'
                                    present+=1
                            elif oc_status=='H':
                                if wo:
                                    oc_status='WO'
                                else:
                                    oc_status=='H'
                                holidays+=1
                                wo=False

                        start_time=datetime.strptime(from_date,'%Y-%m-%d').strftime('%Y-%m-%d 00:00:01')
                        end_time=datetime.strptime(from_date,'%Y-%m-%d').strftime('%Y-%m-%d 23:59:59')
                        att_rec=self.env['nf.biometric'].sudo().search([('emp_id','=',emp_rec.nf_emp),('attendance_date','>=',start_time),('attendance_date','<=',end_time)],order='attendance_date asc')
                        intime='NA'
                        outime='NA'
                        if att_rec:
                            intime=att_rec[0].attendance_date.split(' ')[1]
                            outime=att_rec[-1].attendance_date.split(' ')[1]
                        data.update({'intime'+str(flag):intime,'outime'+str(flag):outime,'oc'+str(flag):oc_status})
                        from_date=(datetime.strptime(from_date,'%Y-%m-%d')+relativedelta(days=1)).strftime('%Y-%m-%d')
                        intime='NA'
                        outime='NA'
                        flag+=1
                    total_leave=earned+casual+privilege+bereavemt+maternity+paternity
                    holidays=holidays-weekoff
                    final_lop=absent+lop_management
                    payroll_days=total_days-final_lop
                    data.update({'present_days':present,'onduty':onduty,'weekoff':weekoff,'holidays':holidays,'total_leave':total_leave,'lop_balance':lop_balance,'absent':absent,'lop_management':lop_management,'final_lop':final_lop,'total_days':total_days,'payroll_days':payroll_days,'earned':earned,'casual':casual,'privilege':privilege,'bereavemt':bereavemt,'maternity':maternity,'paternity':paternity,'biometric':'NA'})
                    datas.append(data)

                worksheet.write(3, 0,'Employee',bold)
                worksheet.write(3, 1,'Employee ID',bold)
                worksheet.write(3, 2,'Date of Joining',bold)
                worksheet.write(3, 3,'Designation',bold)
                worksheet.write(3, 4,'Department',bold)
                worksheet.write(3, 5,'Division',bold)
                worksheet.write(3, 6,'Branch',bold)
                worksheet.write(3, 7,'Work Location',bold)
                worksheet.write(3, 8,'State',bold)
                worksheet.write(3, 9,'Work Email',bold)
                worksheet.write(3, 10,'Reporting Head',bold)
                worksheet.write(3, 11,'Manager',bold)
                worksheet.write(3, 12,'Biometric Status',bold)
                z=y
                y=12
                while y<z:
                    worksheet.write(3, y+1,'First Punch',bold)
                    worksheet.write(3, y+2,'Last Punch',bold)
                    worksheet.write(3, y+3,'OC',bold)
                    y+=3
                worksheet.write(3, y+1,'Present Days',bold)
                #worksheet.write(3, y+2,'On Duty',bold)
                worksheet.write(3, y+2,'Week Off',bold)
                worksheet.write(3, y+3,'Holidays',bold)
                worksheet.write(3, y+4,'EL',bold)
                worksheet.write(3, y+5,'CL/SL',bold)
                worksheet.write(3, y+6,'MT',bold)
                worksheet.write(3, y+7,'PT',bold)
                worksheet.write(3, y+8,'PL',bold)
                worksheet.write(3, y+9,'BL',bold)
                worksheet.write(3, y+10,'Total Leaves Applied',bold)
                #worksheet.write(3, y+11,'LOP as per Leave Balance',bold)
                worksheet.write(3, y+11,'Absent',bold)
                worksheet.write(3, y+12,'LOP as per Management',bold)
                worksheet.write(3, y+13,'Final LOP',bold)
                worksheet.write(3, y+14,'Total Days',bold)
                worksheet.write(3, y+15,'Payroll Days',bold)
            
            x=4
            for data in datas:
                worksheet.write(x, 0, data.get('employee'))
                worksheet.write(x, 1, data.get('emp_id') or 'NA')
                worksheet.write(x, 2, data.get('doj') or 'NA')
                worksheet.write(x, 3, data.get('designation') or 'NA')
                worksheet.write(x, 4, data.get('department'))
                worksheet.write(x, 5, data.get('division'))
                worksheet.write(x, 6, data.get('branch'))
                worksheet.write(x, 7, data.get('work_location'))
                worksheet.write(x, 8, data.get('state'))
                worksheet.write(x, 9, data.get('work_email'))
                worksheet.write(x, 10, data.get('reporting_head'))
                worksheet.write(x, 11, data.get('manager'))
                worksheet.write(x, 12, data.get('biometric'))
                flag1=1
                y=12
                while flag1<=flag:
                    worksheet.write(x, y+1, data.get('intime'+str(flag1)))
                    worksheet.write(x, y+2, data.get('outime'+str(flag1)))
                    worksheet.write(x, y+3, data.get('oc'+str(flag1)))
                    flag1+=1
                    y+=3
                y=y-3
                worksheet.write(x, y+1, data.get('present_days'))
                #worksheet.write(x, y+2, data.get('onduty'))
                worksheet.write(x, y+2, data.get('weekoff'))
                worksheet.write(x, y+3, data.get('holidays'))
                worksheet.write(x, y+4, data.get('earned'))
                worksheet.write(x, y+5, data.get('casual'))
                worksheet.write(x, y+6, data.get('maternity'))
                worksheet.write(x, y+7, data.get('paternity'))
                worksheet.write(x, y+8, data.get('privilege'))
                worksheet.write(x, y+9, data.get('bereavemt'))
                worksheet.write(x, y+10, data.get('total_leave'))
                #worksheet.write(x, y+12, data.get('lop_balance'))
                worksheet.write(x, y+11, data.get('absent'))
                worksheet.write(x, y+12, data.get('lop_management'))
                worksheet.write(x, y+13, data.get('final_lop'))
                worksheet.write(x, y+14, data.get('total_days'))
                worksheet.write(x, y+15, data.get('payroll_days'))
                x+=1
            workbook.close()
            fp.seek(0)
            data = fp.read()
            fp.close()
            out=base64.encodestring(data)
            #writing data in the fields
            i.write({'file_data':out, 'file_name':'attendance_leave_report.xls','hide_field':True})
            return {
                    'name':'Attendance and Leave Report',
                    'res_model':'wiz.attendance.leave.report',
                    'type':'ir.actions.act_window',
                    'view_type':'form',
                    'view_mode':'form',
                    'target':'new',
                    'nodestroy': True,
                    'res_id': i.id
                    }