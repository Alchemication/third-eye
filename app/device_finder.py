# Usage: python device_finder.py

import subprocess
import re
import logging
from datetime import datetime
from config import SUBNET_MASK, HOME_OWNERS_MAC_ADDR
from database import Session
from models import HomeOccupancy


def main():
    """
    Find devices of home owners in local network and save
    in the database if change is detected vs previous run
    """

    # construct command
    CMD = f'sudo nmap -sn {SUBNET_MASK}'
    logging.info(f'Executing cmd: {CMD}')

    # execute CLI process
    p = subprocess.Popen(CMD.split(' '), stdout=subprocess.PIPE)
    out, err = p.communicate()

    # extract Mac addresses in local network
    mac_addresses = [m[0] for m in re.findall(r'(([0-9a-fA-F:]){17})', str(out))]

    # find devices of interest
    cfg_mac_addr = [d['mac_addr'] for d in HOME_OWNERS_MAC_ADDR]
    cfg_owner_names = [d['owner'] for d in HOME_OWNERS_MAC_ADDR]

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
        return
    elif len(idx) == 0 and last_hoc.occupancy_status == 'away':
        last_hoc.update_ts = now
        Session.add(last_hoc)
        Session.commit()
        logging.info(f'Last occupancy status was already away, update_ts column modified')
        return

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


if __name__ == "__main__":
    logging.basicConfig(format="%(asctime)s.%(msecs)03f %(levelname)s %(message)s",
                        level=logging.INFO, datefmt="%H:%M:%S")
    logger = logging.getLogger()
    # logger.setLevel(logging.DEBUG)
    logger.setLevel(logging.INFO)
    main()
