from models import Alert, HomeOccupancy
from database import Session
from datetime import datetime, timedelta
import config


last_alert_check_time = str(datetime.now() - timedelta(seconds=config.SEC_BETWEEN_ALERTS))
found_alert = (Session
               .query(Alert)
               .filter(Alert.create_ts >= last_alert_check_time)
               .order_by(Alert.create_ts.desc())
               .first())
print(found_alert.create_ts)

# min_occupancy_time = str(datetime.now() - timedelta(minutes=config.OWNERS_OUTSIDE_HOME_MIN))
#
# print('MIN:', min_occupancy_time)
#
# last_at_home = (db_sess
#                 .query(HomeOccupancy)
#                 .filter(HomeOccupancy.occupancy_status == 'home', HomeOccupancy.update_ts >= min_occupancy_time)
#                 .order_by(HomeOccupancy.update_ts.desc())
#                 .first())
# # print(last_at_home.id)
# # print(last_at_home.occupancy_status)
# # print(last_at_home.found_owners)
# # print(last_at_home.create_ts)
# # print(last_at_home.update_ts)
