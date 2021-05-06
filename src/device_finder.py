# Usage: python device_finder.py

import subprocess
import re
import logging
from datetime import datetime
import config
from database import Session
from models import HomeOccupancy
import traceback
import sys
import time


def main():
    """
    Find devices of home owners in local network and save
    in the database if change is detected vs previous run
    """

    # how many seconds to sleep for between checks
    SLEEP_TIME = 20

    try:
        while True:  # receive images until Ctrl-C is pressed
            # construct command
            CMD = f'/usr/bin/sudo /usr/bin/nmap -sn {config.SUBNET_MASK}'
            logging.info(f'Executing cmd: {CMD}')

            # execute CLI process
            p = subprocess.Popen(CMD.split(' '), stdout=subprocess.PIPE)
            out, err = p.communicate()

            # extract Mac addresses in local network
            mac_addresses = [m[0] for m in re.findall(r'(([0-9a-fA-F:]){17})', str(out))]

            # find devices of interest
            cfg_mac_addr = [d['mac_addr'] for d in config.HOME_OWNERS_MAC_ADDR]
            cfg_owner_names = [d['owner'] for d in config.HOME_OWNERS_MAC_ADDR]

            # find indexes of devices found in the network
            idx = []
            for m in mac_addresses:
                if m in cfg_mac_addr:
                    idx.append(cfg_mac_addr.index(m))

            # useful initializations
            now = datetime.now()

            # fetch last occupancy
            last_hoc = Session.query(HomeOccupancy).order_by(HomeOccupancy.id.desc()).first()

            # check if status needs to be changed to away
            if len(idx) == 0 and (last_hoc is None or last_hoc.occupancy_status == 'home'):
                new_hoc = HomeOccupancy(create_ts=now, update_ts=now, occupancy_status='away')
                Session.add(new_hoc)
                Session.commit()
                logging.info(f'Last occupancy status changed to: away')
                # wait for a while before next iteration
                logging.info(f'Wait for {SLEEP_TIME} seconds')
                time.sleep(SLEEP_TIME)
                continue
            elif len(idx) == 0 and last_hoc.occupancy_status == 'away':
                last_hoc.update_ts = now
                Session.add(last_hoc)
                Session.commit()
                logging.info(f'Last occupancy status was already away, update_ts column modified')
                # wait for a while before next iteration
                logging.info(f'Wait for {SLEEP_TIME} seconds')
                time.sleep(SLEEP_TIME)
                continue

            # at this point we do have home owners, so let's check if we are switching
            # from away, or only updating update_ts
            owner_names = [cfg_owner_names[i] for i in idx]
            if last_hoc is None or last_hoc.occupancy_status == 'away':
                new_hoc = HomeOccupancy(create_ts=now, update_ts=now, occupancy_status='home',
                                        found_owners=owner_names)
                Session.add(new_hoc)
                Session.commit()
                logging.info(f'Last occupancy status changed to: home')
            elif last_hoc.occupancy_status == 'home':
                last_hoc.update_ts = now
                last_hoc.found_owners = owner_names
                Session.add(last_hoc)
                Session.commit()
                logging.info(f'Last occupancy status was already home, update_ts column modified')

            # wait for a while before next iteration
            logging.info(f'Wait for {SLEEP_TIME} seconds')
            time.sleep(SLEEP_TIME)
    except (KeyboardInterrupt, SystemExit):
        pass  # Ctrl-C was pressed to end program
    except Exception as e:
        logging.error(f'Python error with no Exception handler: {str(e)}')
        logging.error(str(traceback.print_exc()))
    finally:
        sys.exit()


if __name__ == "__main__":
    logging.basicConfig(format=config.LOGGING_FORMAT, level=config.LOGGING_LEVEL, datefmt="%H:%M:%S")
    logger = logging.getLogger()
    main()
