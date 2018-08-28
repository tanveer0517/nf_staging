from openerp import api, fields, models, _
import time
from datetime import datetime,timedelta
from dateutil.relativedelta import relativedelta
import calendar
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib2 import Request, urlopen
import json,urllib,urllib2
import smtplib
import StringIO
import base64
import csv
from email.mime.application import MIMEApplication

fos_desig = ('Associate - FOS','Consultant - FOS','Principal Consultant - FOS','Senior Consultant - FOS','Associate Product Specialist',
'Principal Product Specialist','Product Specialist','Senior Product Specialist','Associate - Verticals','Consultant - Verticals',
'Principal Consultant - Verticals','Senior Consultant - Verticals')

team_lead_desig = ('Assistant Team Leader', 'Assistant Team Lead - FOS', 'Associate Team Lead', 'Team Lead - FOS', 'Team Leader - Rest Of State', 'Team Leader', 'Team Lead - Product Specialist')

cf_desig = ('Associate - Customer First','Consultant - Customer First','Principal Consultant - Customer First','Senior Consultant - Customer First')

class nf_schedular(models.Model):
    _name = "nf.schedular"
    
    @api.model
    def allocation_leave(self):
        self.env.cr.execute("select leave_allocation(Null)")
        return True

    @api.model
    def send_non_swipe_bm(self):
        cr = self.env.cr
        synq_bmtc = self.env['nf.biometric'].sync_biometric_data()
        date = fields.Date.context_today(self)
        date = datetime.strptime(date, '%Y-%m-%d')
        current_day = calendar.day_name[date.weekday()]
        if current_day != 'Sunday':
            date = date.strftime('%d-%b-%Y')
            rec = """ """
            cc = []

            str_sql = "SELECT " \
                      "DISTINCT COALESCE(emp.nf_emp,'')," \
                      "emp.name_related AS name," \
                      "(SELECT name FROM hr_branch WHERE id = emp.branch_id) AS branch," \
                      "emp.branch_id AS branch_id," \
                      "COALESCE(emp.work_email,'') AS bm_email," \
                      "COALESCE((SELECT work_email FROM hr_employee where id = emp.parent_id),'') AS bm_manager_email " \
                      "FROM hr_employee emp " \
                      "LEFT JOIN resource_resource res ON emp.resource_id = res.id " \
                      "WHERE res.active = True " \
                      "AND emp.intrnal_desig = 'Branch Manager' " \
                      "AND emp.nf_emp NOT IN (SELECT emp_id FROM nf_biometric WHERE attendance_date::date = 'now'::date) " \
                      "ORDER BY emp.name_related"

            cr.execute(str_sql)
            temp = cr.fetchall()

            param = self.env['ir.config_parameter']
            BranchWithoutBiometric = param.search([('key', '=', 'BranchWithoutBiometric')])
            BranchWithoutBiometric = map(int, BranchWithoutBiometric.value.split(','))

            for val in temp:
                emp_id = val[0]
                name = val[1]
                branch = val[2]
                if val[3] in BranchWithoutBiometric:
                    fnt_clr = "grey"
                    bmtc_sts = 'NA'
                else:
                    fnt_clr = "red"
                    bmtc_sts = 'Working'
                    cc.extend((val[4], val[5]))

                rec = rec + """<tr width="100%" style="border-top: 1px solid black;border-bottom: 1px solid black;">
    										  <td width="20% class="text-left"><font color=""" + str(
                    fnt_clr) + """>""" + str(emp_id) + """</font></td>
    										  <td width="30%" class="text-left"><font color=""" + str(
                    fnt_clr) + """>""" + str(name) + """</font></td>
    										  <td width="30%" class="text-left"><font color=""" + str(
                    fnt_clr) + """>""" + str(branch) + """</font></td>
    										  <td width="20%" class="text-left"><font color=""" + str(
                    fnt_clr) + """>""" + str(bmtc_sts or '') + """</font></td>

    					<tr>
    					<tr width="100%" colspan="6" height="5"></tr>"""

            mail_subject = "Details of BM not in Office/Absent on %s, TIME STAMP : 11 AM" % date

            heading = "Please find details of BM not in Office/Absent on %s, TIME STAMP : 11 AM" % date

            html = """<!DOCTYPE html>
    						 <html>

    						   <body>
    							 <p style="color:#4E0879">  <b>Dear Team,</b></p>
    							 <table style="width:100%">
    								  <tr>
    									 <td style="color:#4E0879"><left><b><span>""" + str(heading) + """</span></b></center></td>
    								  </tr>
    							 </table>
    								  <br/>
    							 <table width="100%" style="border-top: 1px solid black;border-bottom: 1px solid black;">
    							 <tr width="100%" class="border-black">
    								  <td width="20%" class="text-left" style="border-bottom: 1px solid black;"> <b>Emp ID</b> </td>
    								  <td width="30%"  class="text-left" style="border-bottom: 1px solid black;"> <b>Name</b> </td>
    								  <td width="30%" class="text-left" style="border-bottom: 1px solid black;"> <b>Branch</b> </td>
    								  <td width="20%" class="text-left" style="border-bottom: 1px solid black;"> <b>Att Machine Status</b> </td>
    							  </tr>

    								  """ + str(rec) + """
    							</table>
    						</body>

    						<div>
    							<p></p>
    						</div>
    							<html>"""

            msg = MIMEMultipart()
            emailfrom = "erpnotification@nowfloats.com"
            toaddr = ['raunak.ansari@nowfloats.com', 'satesh.kohli@nowfloats.com', 'anurupa.singh@nowfloats.com',
                      'nitin@nowfloats.com', 'richa.gaur@nowfloats.com',
                      'mohit.katiyar@nowfloats.com']
            msg['From'] = emailfrom
            msg['To'] = ", ".join(toaddr)
            msg['CC'] = ", ".join(cc)
            msg['Subject'] = mail_subject
            emailto = toaddr + cc

            part1 = MIMEText(html, 'html')
            msg.attach(part1)
            cr.execute("SELECT smtp_user,smtp_pass FROM ir_mail_server WHERE name = 'erpnotification'")
            mail_server = cr.fetchone()
            smtp_user = mail_server[0]
            smtp_pass = mail_server[1]
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.login(smtp_user, smtp_pass)
            text = msg.as_string()
            try:
                server.sendmail(emailfrom, emailto, text)
            except:
                pass
            server.quit()
        return True

    @api.model
    def birthday_notification(self):
        curr_date = datetime.now().strftime("%m-%d")
        for rec in self.env['hr.employee'].sudo().search([('active','=',True)]):
            birthday = rec.birthday
            if birthday:
                birthday = birthday[5:10]
                if birthday == curr_date:
                    temp_id = self.env['mail.template'].search([('name', '=', 'Birthday Notification')])
                    if temp_id:
                        temp_id.send_mail(rec.id)

        return True

    @api.model
    def work_anniversary_notification(self):
        current_date = datetime.now()
        curr_date = current_date.strftime("%m-%d")
        curr_year = current_date.year
        for rec in self.env['hr.employee'].sudo().search([('active','=',True)]):
            joining_date = rec.join_date
            if joining_date:
                join_date = joining_date[5:10]
                join_year = joining_date[0:4]
                duration = curr_year - int(join_year)
                if join_date == curr_date:
                    if rec.gender == 'male':
                        if duration == 1:
                            temp_id1 = self.env['mail.template'].search(
                                [('name', '=', 'Work Anniversary Notification Male 1 Year')])
                            if temp_id1:
                                temp_id1.send_mail(rec.id)
                        elif duration == 2:
                            temp_id2 = self.env['mail.template'].search(
                                [('name', '=', 'Work Anniversary Notification Male 2 Years')])
                            if temp_id2:
                                temp_id2.send_mail(rec.id)
                        elif duration == 3:
                            temp_id3 = self.env['mail.template'].search(
                                [('name', '=', 'Work Anniversary Notification Male 3 Years')])
                            if temp_id3:
                                temp_id3.send_mail(rec.id)
                        elif duration == 4:
                            temp_id4 = self.env['mail.template'].search(
                                [('name', '=', 'Work Anniversary Notification Male 4 Years')])
                            if temp_id4:
                                temp_id4.send_mail(rec.id)
                        elif duration == 5:
                            temp_id4 = self.env['mail.template'].search(
                                [('name', '=', 'Work Anniversary Notification Male 5 Years')])
                            if temp_id4:
                                temp_id4.send_mail(rec.id)
                        elif duration == 6:
                            temp_id4 = self.env['mail.template'].search(
                                [('name', '=', 'Work Anniversary Notification Male 6 Years')])
                            if temp_id4:
                                temp_id4.send_mail(rec.id)
                    elif rec.gender == 'female':
                        if duration == 1:
                            temp_id1 = self.env['mail.template'].search(
                                [('name', '=', 'Work Anniversary Notification Female 1 Year')])
                            if temp_id1:
                                temp_id1.send_mail(rec.id)
                        elif duration == 2:
                            temp_id2 = self.env['mail.template'].search(
                                [('name', '=', 'Work Anniversary Notification Female 2 Years')])
                            if temp_id2:
                                temp_id2.send_mail(rec.id)
                        elif duration == 3:
                            temp_id3 = self.env['mail.template'].search(
                                [('name', '=', 'Work Anniversary Notification Female 3 Years')])
                            if temp_id3:
                                temp_id3.send_mail(rec.id)
                        elif duration == 4:
                            temp_id4 = self.env['mail.template'].search(
                                [('name', '=', 'Work Anniversary Notification Female 4 Years')])
                            if temp_id4:
                                temp_id4.send_mail(rec.id)
                        elif duration == 5:
                            temp_id4 = self.env['mail.template'].search(
                                [('name', '=', 'Work Anniversary Notification Female 5 Years')])
                            if temp_id4:
                                temp_id4.send_mail(rec.id)
                        elif duration == 6:
                            temp_id4 = self.env['mail.template'].search(
                                [('name', '=', 'Work Anniversary Notification Female 6 Years')])
                            if temp_id4:
                                temp_id4.send_mail(rec.id)

        return True

    @api.model
    def absconding_notification(self):
        curr_date = datetime.now().strftime("%Y-%m-%d")
        for rec in self.env['termination'].sudo().search([]):
            if rec.date_of_leaving == curr_date:
                temp_id = self.env['mail.template'].search([('name', '=', 'Absconding Notification')])
                if temp_id:
                    temp_id.send_mail(rec.id)

        return True

    @api.model
    def probation_notification(self):
        date_join = (datetime.now() - relativedelta(months=3)).strftime("%Y-%m-%d")
        for rec in self.env['hr.employee'].sudo().search([('join_date','=',date_join)]):
            if rec:
                res=self.env['nf.employee.probation'].sudo().create({'employee_id':rec.id})
                res.employee_id.sudo().write({'probation_completed': True})

        return True

    @api.model
    def probation_extend_notification(self):
        curr_date = (datetime.now()).strftime("%Y-%m-%d")
        for res in self.env['nf.employee.probation'].sudo().search([('extend_date','=',curr_date)]):
            if res:
                temp_id = self.env['mail.template'].search([('name', '=', 'Probation Extend Notification')])
                if temp_id:
                    temp_id.send_mail(res.id)

        return True

    @api.model
    def mlc_onboarding_notification(self):
        start_date = '2018-05-31 00:00:01'
        so_obj = self.env['sale.order']
        so_rec = so_obj.sudo().search([('c_auto_create_fptag','=',True),('confirmation_date','>=',start_date),('onboarding_done','!=',True),('is_kitsune','!=',True)])
        for rec in so_rec:
            if rec:
                temp_id = self.env['mail.template'].search([('name', '=', 'MLC Onboarding Not Done Notification')])
                if temp_id:
                    temp_id.send_mail(rec.id)
        return True

    @api.model
    def get_fos_lop_count(self, number, attendance_status):
        cr = self.env.cr
        if number == 0:
            str_sql = "SELECT COUNT(emp.id) " \
                      "FROM hr_employee emp LEFT JOIN resource_resource res ON emp.resource_id = res.id " \
                      "LEFT JOIN nf_leave_swipe leave ON res.user_id = leave.user_id " \
                      "WHERE res.active = True AND " \
                      "emp.intrnal_desig IN {} " \
                      "AND leave.attendance_status = '{}' AND " \
                      "leave.date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date " \
                      "AND res.user_id NOT IN (SELECT user_id FROM crm_phonecall " \
                      "WHERE date::date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date) " \
                .format(fos_desig, attendance_status)
        elif number in (1, 2, 3):
            str_sql = "WITH SLOT AS (SELECT COUNT(id) AS cn " \
                      "FROM crm_phonecall " \
                      "WHERE date::date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date " \
                      "AND user_id IN (SELECT res.user_id FROM hr_employee emp " \
                      "LEFT JOIN resource_resource res ON emp.resource_id = res.id " \
                      "LEFT JOIN nf_leave_swipe leave ON res.user_id = leave.user_id " \
                      "WHERE res.active = True AND emp.intrnal_desig IN {} " \
                      "AND leave.attendance_status = '{}' AND " \
                      "leave.date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date) GROUP BY user_id) " \
                      "SELECT COUNT(*) AS cn1 " \
                      "FROM SLOT WHERE cn = {}" \
                .format(fos_desig, attendance_status, number)
        else:
            str_sql = "WITH SLOT AS (SELECT COUNT(id) AS cn " \
                      "FROM crm_phonecall " \
                      "WHERE date::date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date " \
                      "AND user_id IN (SELECT res.user_id FROM hr_employee emp " \
                      "LEFT JOIN resource_resource res ON emp.resource_id = res.id " \
                      "LEFT JOIN nf_leave_swipe leave ON res.user_id = leave.user_id " \
                      "WHERE res.active = True AND emp.intrnal_desig IN {} " \
                      "AND leave.attendance_status = '{}' AND " \
                      "leave.date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date) GROUP BY user_id) " \
                      "SELECT COUNT(*) AS cn1 " \
                      "FROM SLOT WHERE cn > 3" \
                .format(fos_desig, attendance_status)
        cr.execute(str_sql)
        temp = cr.fetchone()
        return temp

    @api.model
    def get_fos_meeting_count(self, number):
        if number == 0:
            str_sql = "SELECT COUNT(emp.id) " \
                      "FROM hr_employee emp LEFT JOIN resource_resource res ON emp.resource_id = res.id  " \
                      "WHERE res.active = True AND " \
                      "emp.intrnal_desig IN {} " \
                      "AND res.user_id NOT IN (SELECT user_id FROM crm_phonecall " \
                      "WHERE date::date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date)"\
                .format(fos_desig)
        elif number in (1, 2, 3):
            str_sql = "WITH SLOT AS (SELECT COUNT(id) AS cn " \
                      "FROM crm_phonecall " \
                      "WHERE date::date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date " \
                      "AND user_id IN (SELECT res.user_id FROM hr_employee emp " \
                      "LEFT JOIN resource_resource res ON emp.resource_id = res.id " \
                      "WHERE res.active = True AND emp.intrnal_desig IN {}) GROUP BY user_id) " \
                      "SELECT COUNT(*) AS cn1 " \
                      "FROM SLOT WHERE cn = {}"\
                .format(fos_desig, number)
        else:
            str_sql = "WITH SLOT AS (SELECT COUNT(id) AS cn " \
                      "FROM crm_phonecall " \
                      "WHERE date::date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date " \
                      "AND user_id IN (SELECT res.user_id FROM hr_employee emp " \
                      "LEFT JOIN resource_resource res ON emp.resource_id = res.id " \
                      "WHERE res.active = True AND emp.intrnal_desig IN {}) GROUP BY user_id) " \
                      "SELECT COUNT(*) AS cn1 " \
                      "FROM SLOT WHERE cn > 3" \
                .format(fos_desig)
        self.env.cr.execute(str_sql)
        temp = self.env.cr.fetchone()
        return temp

    @api.model
    def get_meeting_count_file(self):
        cr = self.env.cr
        fp = StringIO.StringIO()
        writer = csv.writer(fp)
        cr.execute("SELECT "
                            "cm.date::date AS date, "
                            "emp.name_related AS employee, "
                            "emp.work_email AS email, "
                            "COUNT(cm.id) AS meeting_count,"
                            "(SELECT name FROM hr_branch WHERE id = emp.branch_id) AS branch,"
                            "emp.intrnal_desig AS emp_designation,"
                            "(SELECT attendance_status FROM nf_leave_swipe WHERE user_id = res.user_id "
                            "AND date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date LIMIT 1) AS attendance_status "
                            "FROM crm_phonecall cm LEFT JOIN resource_resource res ON cm.user_id = res.user_id "
                            "LEFT JOIN hr_employee emp ON emp.resource_id = res.id "
                            "WHERE cm.date::date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date "
                            "AND res.active = True AND emp.intrnal_desig IN {} "
                            "GROUP BY cm.date::date, emp.name_related, emp.work_email, (SELECT name FROM hr_branch WHERE id = emp.branch_id), "
                            "emp.intrnal_desig, (SELECT attendance_status FROM nf_leave_swipe WHERE user_id = res.user_id "
                            "AND date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date LIMIT 1) "
                            "ORDER BY emp.name_related".format(fos_desig))
        writer.writerow([i[0] for i in cr.description])
        temp1 = cr.fetchall()
        for val in temp1:
            writer.writerow(val)

        cr.execute("SELECT (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date AS date, "
                   "emp.name_related AS employee, "
                   "emp.work_email AS email, "
                   " 0 AS meeting_count, "
                   "(SELECT name FROM hr_branch WHERE id = emp.branch_id) AS branch,"
                   "emp.intrnal_desig AS emp_designation,"
                   "(SELECT attendance_status FROM nf_leave_swipe WHERE user_id = res.user_id "
                   "AND date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date LIMIT 1) AS attendance_status " \
                  "FROM hr_employee emp LEFT JOIN resource_resource res ON emp.resource_id = res.id  " \
                  "WHERE res.active = True AND " \
                  "emp.intrnal_desig IN {} " \
                  "AND res.user_id NOT IN (SELECT user_id FROM crm_phonecall " \
                  "WHERE date::date = (NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date)" \
            .format(fos_desig))
        temp2 = cr.fetchall()
        for val in temp2:
            writer.writerow(val)

        fp.seek(0)
        data = fp.read()
        fp.close()
        data = base64.encodestring(data)
        return data

    @api.model
    def send_number_of_meeting_details(self):
        cr = self.env.cr

        sync_bmtc = self.env['nf.biometric'].sync_biometric_data()
        if not sync_bmtc:
            return False
        cr.execute("SELECT * FROM update_swipe_leave_attendance()")

        date = fields.Date.context_today(self)
        date = datetime.strptime(date, '%Y-%m-%d')
        current_day = calendar.day_name[date.weekday()]
        if current_day != 'Monday':
            date = date - relativedelta(days=1)
            date = date.strftime('%d-%b-%Y')
            cc = ['mohit.katiyar@nowfloats.com']

            cn1 = self.get_fos_meeting_count(1)[0]
            cn2 = self.get_fos_meeting_count(2)[0]
            cn3 = self.get_fos_meeting_count(3)[0]
            cn4 = self.get_fos_meeting_count(4)[0]

            cn5 = self.get_fos_meeting_count(0)[0]

            total_fos = cn1 + cn2 + cn3 + cn4 + cn5

            acn1 = self.get_fos_lop_count(1, 'A')[0]
            acn2 = self.get_fos_lop_count(2, 'A')[0]
            acn3 = self.get_fos_lop_count(3, 'A')[0]
            acn4 = self.get_fos_lop_count(4, 'A')[0]

            acn5 = self.get_fos_lop_count(0, 'A')[0]

            total_absent_fos = acn1 + acn2 + acn3 + acn4 + acn5

            lcn1 = self.get_fos_lop_count(1, 'L')[0]
            lcn2 = self.get_fos_lop_count(2, 'L')[0]
            lcn3 = self.get_fos_lop_count(3, 'L')[0]
            lcn4 = self.get_fos_lop_count(4, 'L')[0]

            lcn5 = self.get_fos_lop_count(0, 'L')[0]

            total_leave_fos = lcn1 + lcn2 + lcn3 + lcn4 + lcn5

            msg = MIMEMultipart()
            data = self.get_meeting_count_file()
            file_name = 'meeting_count_by_fos.csv'

            data = base64.b64decode(data)
            part = MIMEApplication(
                data,
                Name=file_name
            )
            part['Content-Disposition'] = 'attachment; filename="{}"' \
                .format(file_name)
            msg.attach(part)

            mail_subject = "FOS-India Meeting Count On %s" % date

            heading = "FOS-India Meeting count on %s" % date

            html = """<!DOCTYPE html>
                                 <html>

                                   <body>
                                     <table style="width:100%">
                                          <tr>
                                             <td style="color:#4E0879"><left><b><span>""" + str(heading) + """</span></b></left></td>
                                          </tr>
                                     </table>
                                          <br/>
                                     <table style="width:100%">
                                         <tr style="width:100%">
                                             <td style="width:20%"><font color= "red"/><b>Meeting Count</b></td>
                                             <td class="text-left" style="width:20%"><font color= "red"/>: <b>FOS-Total Count (<span>""" +str(total_fos)+"""<span>)</b></span></td>
                                             <td class="text-left" style="width:20%"><font color= "red"/> <b>FOS-Legal Leaves Count (<span>""" + str(
                    total_leave_fos) + """<span>)</b></span></td>
                                                    <td class="text-left" style="width:20%"><font color= "red"/> <b>FOS-LOP Count (<span>""" + str(
                    total_absent_fos) + """<span>)</b></span></td>
                                             <td style="width:20%"></td>
                                          </tr>
                                          <tr style="width:100%">
                                             <td style="width:20%"><b>0 Meeting</b></td>
                                             <td class="text-left" style="width:20%">: <span>""" + str(cn5) + """</span></td>
                                             <td class="text-left" style="width:20%"> <span>""" + str(lcn5) + """</span></td>
                                             <td class="text-left" style="width:20%"> <span>""" + str(acn5) + """</span></td>
                                             <td style="width:20%"></td>
                                          </tr>
                                          <tr style="width:100%">
                                             <td style="width:20%"><b>1 Meeting</b></td>
                                             <td class="text-left" style="width:20%">: <span>""" + str(cn1) + """</span></td>
                                             <td class="text-left" style="width:20%"> <span>""" + str(lcn1) + """</span></td>
                                             <td class="text-left" style="width:20%"> <span>""" + str(acn1) + """</span></td>
                                             <td style="width:20%"></td>
                                          </tr>
                                          <tr style="width:100%">
                                             <td style="width:20%"><b>2 Meeting</b></td>
                                             <td class="text-left" style="width:20%">: <span>""" + str(cn2) + """</span></td>
                                             <td class="text-left" style="width:20%"> <span>""" + str(lcn2) + """</span></td>
                                             <td class="text-left" style="width:20%"> <span>""" + str(acn2) + """</span></td>
                                             <td style="width:20%"></td>
                                          </tr>
                                      <tr style="width:100%">
                                             <td style="width:20%"><b>3 Meeting</b></td>
                                             <td class="text-left" style="width:20%">: <span>""" + str(cn3) + """</span></td>
                                             <td class="text-left" style="width:20%"> <span>""" + str(lcn3) + """</span></td>
                                             <td class="text-left" style="width:20%"> <span>""" + str(acn3) + """</span></td>
                                             <td style="width:20%"></td>
                                          </tr>
                                      <tr style="width:100%">
                                             <td style="width:20%"><b>3+ Meeting</b></td>
                                             <td class="text-left" style="width:20%">: <span>""" + str(cn4) + """</span></td>
                                             <td class="text-left" style="width:20%"> <span>""" + str(lcn4) + """</span></td>
                                             <td class="text-left" style="width:20%"> <span>""" + str(acn4) + """</span></td>
                                             <td style="width:20%"></td>
                                          </tr>
                                      <tr style="width:100%">
                                             <td style="width:20%"></td>
                                             <td style="width:20%"></td>
                                             <td style="width:20%"></td>
                                             <td style="width:20%"></td>
                                             <td style="width:20%"></td>
                                          </tr>
                                    </table>
                                    <p> <i> PFA for details </i> </p>
                                   <p>----------------------------------------------------------------------------------------------</p>
                                </body>

                            <html>"""


            emailfrom = "erpnotification@nowfloats.com"
            toaddr = ['nitin@nowfloats.com', 'salesaudit@nowfloats.com', 'satesh.kohli@nowfloats.com', 'richa.gaur@nowfloats.com', 'neha.shrikhande@nowfloats.com', 'anurupa.singh@nowfloats.com']
            msg['From'] = emailfrom
            msg['To'] = ", ".join(toaddr)
            msg['CC'] = ", ".join(cc)
            msg['Subject'] = mail_subject
            emailto = toaddr + cc

            part1 = MIMEText(html, 'html')
            msg.attach(part1)
            cr.execute("SELECT smtp_user,smtp_pass FROM ir_mail_server WHERE name = 'erpnotification'")
            mail_server = cr.fetchone()
            smtp_user = mail_server[0]
            smtp_pass = mail_server[1]
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.login(smtp_user, smtp_pass)
            text = msg.as_string()
            try:
                server.sendmail(emailfrom, emailto, text)
            except:
                pass
            server.quit()
        return True
    

    @api.model
    def get_buddy(self):
        cr=self.env.cr
        buddy_desig = fos_desig+team_lead_desig+cf_desig
        last_day=11
        curr_date=datetime.now()
        curr_day=curr_date.weekday()
        if curr_day in (2,3,4,5,6):
            last_day=12
        last_date=(curr_date+relativedelta(days=last_day)).strftime('%Y-%m-%d')
        emp_rec_ids = self.env['hr.employee'].sudo().search([('c_ldt','=',curr_date.strftime('%Y-%m-%d')),('c_nf_buddy','!=',False)])
        if emp_rec_ids:
            for emp_rec in emp_rec_ids:
                cand_vals=[]
                buddy_vals=[]
                ques_rec=self.env['nf.buddy.feedback.question']
                candidate_question_ids = ques_rec.sudo().search([('type','=','Candidate')])
                buddy_question_ids = ques_rec.sudo().search([('type','=','Buddy')])
                for cand_res in candidate_question_ids:
                    cand_vals.append((0,False,{'name':cand_res.name}))
                for buddy_res in buddy_question_ids:
                    buddy_vals.append((0,False,{'name':buddy_res.name}))
                feedback_id = self.env['nf.buddy.candidate.feedback'].sudo().create({'employee_id':emp_rec.id,'buddy_id':emp_rec.c_nf_buddy.id,'training_start_date':emp_rec.buddy_assign_date,'training_end_date':emp_rec.c_ldt,'candidate_feedback':cand_vals,'buddy_feedback':buddy_vals})
                temp_id = self.env['mail.template'].search([('name', '=', 'Training Feedback for Employee and Buddy')])
                if temp_id:
                    temp_id.send_mail(feedback_id.id)
        cr.execute("UPDATE hr_employee SET c_nf_buddy = Null,c_nf_trainee = Null, c_ldt = Null, buddy_assign_date = NULL WHERE c_ldt <= 'now'::date")
        str_sql1 = "SELECT " \
                   "emp.id," \
                   "emp.branch_id AS branch " \
                   "FROM hr_employee emp " \
                   "WHERE emp.c_pathsala_date + INTERVAL '7 days' = 'now'::date " \
                   "AND emp.intrnal_desig IN {}".format(buddy_desig)
        cr.execute(str_sql1)
        new_emp = cr.fetchall()
        for val in new_emp:
            str_sql2 = "SELECT " \
                       "emp_db_id," \
                       "employee," \
                       "nf_emp " \
                       "FROM " \
                       "nf_buddy_view " \
                       "WHERE branch_id = {} AND so_number > 3 " \
                       "AND emp_db_id NOT IN (SELECT id FROM hr_employee WHERE c_ldt IS NOT NULL) ORDER BY rank LIMIT 1" \
                .format(val[1])
            cr.execute(str_sql2)
            buddy = cr.fetchone()
            if buddy:
                cr.execute("UPDATE hr_employee SET c_nf_buddy = %s,c_ldt = %s,buddy_assign_date = %s WHERE id = %s",
                           (buddy[0], last_date, curr_date.strftime('%Y-%m-%d'), val[0]))
                cr.execute(
                    "UPDATE hr_employee SET c_nf_trainee = %s,c_ldt = %s WHERE id = %s",
                    (val[0], last_date, buddy[0]))
                try:
                    self.send_buddy_email(buddy[0], 'buddy')
                    self.send_buddy_email(val[0])
                except:
                    pass
        return True

    def send_buddy_email(self, employee, type = 'trainee'):
        cr=self.env.cr
        emp = self.env['hr.employee'].browse(employee)
        if type == 'buddy':
            mail_subject = "You are now a BUDDY at NowFloats"

            html = """<!DOCTYPE html>
                        <html>

                            <body>
                   <p style="color:#4E0879">Welcome """+str(emp.c_nf_trainee.name_related) +"""  to the NowFloats family!</p>
                   <p>To make the on-boarding experience better, you are now a buddy and will be accompanied by """+str(emp.c_nf_trainee.name_related)+""" on your meetings for 10 days after their training at the Paathshala.</p></br>

                <table style="width:100%">
                              <tr style="width:100%">
                                <td style="width:15%"><b>Branch</b></td>
                                <td style="width:55%">: <span>"""+str(emp.branch_id.name)+"""</span></td>
                    <td style="width:30%"></td>
                              </tr>
                              <tr style="width:100%">
                                <td style="width:15%"><b>Contact Number</b></td>
                                <td style="width:55%">: <span>"""+str(emp.c_nf_trainee.mobile_phone)+"""</span></td>
                    <td style="width:30%"></td>
                              </tr>
                  
                  <tr style="width:100%">
                                <td style="width:15%"><b>Email ID</b></td>
                                <td style="width:55%">: <span>"""+str(emp.c_nf_trainee.work_email)+"""</span></td>
                    <td style="width:30%"></td>
                              </tr>
                </table>

                <p></p></br>
            
                <p>Reach out to the new member of the NowFloats family and get to know them better. You are now responsible for providing the best hands-on experience on the field.</p></br>
                <p>All the best!</p>
                            </body>

                    <div>
                        <p></p>
                    </div>
            <html>"""
               
        else:
            mail_subject = "You now have a BUDDY at NowFloats"
        
            html = """<!DOCTYPE html>
                            <html>

                                <body>
                       <p style="color:#4E0879"> Welcome to the NowFloats Family!</p>
                       <p>To make your experience with NowFloats better, you are assigned a buddy whom you must accompany on the field for 10 days after your training at the Paathshala.</p></br>

                    <table style="width:100%">
                                  <tr style="width:100%">
                                     <td style="width:25%"><b>Your Buddy</b></td>
                                    <td style="width:75%">: <span>"""+str(emp.c_nf_buddy.name_related)+"""</span></td>
                                  </tr>
                                  <tr style="width:100%">
                                     <td style="width:25%"><b>Branch Name</b></td>
                                    <td style="width:75%">: <span>"""+str(emp.branch_id.name)+"""</span></td>
                                  </tr>
                                  <tr style="width:100%">
                                     <td style="width:25%"><b>Contact Number of your Buddy</b></td>
                                    <td style="width:75%">: <span>"""+str(emp.c_nf_buddy.mobile_phone)+"""</span></td>
                                  </tr>
                      
                      <tr style="width:100%">
                                     <td style="width:25%"><b>Email ID of your Buddy</b></td>
                                    <td style="width:75%">: <span>"""+str(emp.c_nf_buddy.work_email)+"""</span></td>
                                  </tr>
                    </table>

                    <p></p></br>
                
                    <p>Reach out to your buddy and get to know them better. They will give you a hands-on experience on the field about choosing the right set of customers, pitching and closing the sales.</p></br>
                    <p>All the best!</p>
                                </body>

                        <div>
                            <p></p>
                        </div>
                <html>"""  

        msg = MIMEMultipart()
        emailfrom = "erpnotification@nowfloats.com"
        emailto = [emp.work_email,emp.parent_id and emp.parent_id.work_email or '',emp.branch_id.manager_id and emp.branch_id.manager_id.work_email or '','hrdesk@nowfloats.com','shiksha@nowfloats.com','tanveer.asghar@nowfloats.com']
        msg['From'] = emailfrom
        msg['To'] = ", ".join(emailto)
        msg['Subject'] = mail_subject
        part1 = MIMEText(html, 'html')
        msg.attach(part1)
        cr.execute("SELECT smtp_user,smtp_pass FROM ir_mail_server WHERE name = 'erpnotification'")
        mail_server = cr.fetchone()
        smtp_user = mail_server[0]
        smtp_pass = mail_server[1]
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(smtp_user, smtp_pass)
        text = msg.as_string()
        try:
            server.sendmail(emailfrom, emailto, text)
        except:
            pass
        server.quit()
        return True

    @api.model
    def get_buddy_pending_feedback(self):
        last_date=(datetime.now()-relativedelta(days=1)).strftime('%Y-%m-%d')
        rec_ids = self.env['nf.buddy.candidate.feedback'].sudo().search([('training_end_date','=',last_date)])
        if rec_ids:
            for rec in rec_ids:
                if not rec.candidate_submit or not rec.buddy_submit:
                    temp_id = self.env['mail.template'].sudo().search([('name', '=', 'Buddy Feedback Pending Notification')], limit = 1)
                    if temp_id:
                        temp_id.send_mail(rec.id)

        return True

    @api.model
    def get_buddy_feedback_not_submitted(self):
        last_date=(datetime.now()-relativedelta(days=2)).strftime('%Y-%m-%d')
        rec_ids = self.env['nf.buddy.candidate.feedback'].sudo().search([('training_end_date','=',last_date)])
        if rec_ids:
            for rec in rec_ids:
                if not rec.candidate_submit or not rec.buddy_submit:
                    temp_id = self.env['mail.template'].sudo().search([('name', '=', 'Buddy Feedback Not Submitted Notification')], limit = 1)
                    if temp_id:
                        temp_id.send_mail(rec.id)

        return True