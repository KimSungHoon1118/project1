from db_save import job_fetch_festival  # job_fetch_festival 함수가 정의된 모듈
from apscheduler.schedulers.background import BackgroundScheduler



def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(job_fetch_festival, 'interval', weeks=1, id='fetch_festival_job')
    scheduler.start()