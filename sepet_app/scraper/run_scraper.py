from scrape_runner import main
from apscheduler.schedulers.blocking import BlockingScheduler

if __name__ == "__main__":
    #scheduler = BlockingScheduler()
    #scheduler.add_job(main, 'cron', hour=14)
    #scheduler.add_job(test_job, 'interval', minutes=1)
    #logger.info("Starting scheduler...")
    #scheduler.start()
    main()
