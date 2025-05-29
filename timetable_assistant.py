#!/usr/bin/env python3


from PIL import Image
import sane
import yaml
import pprint
import argparse
import pytesseract
import os
import shutil

from jinja2 import Template
from datetime import datetime
from weasyprint import HTML


def generate_days(year, month):
    '''
    Generate a list of dict's with the number of the day and the name of day
    '''
    days = []
    for day in range(1, 32):
        try:
            date = datetime(year, month, day)
            days.append({'day': date.day, 'day_name': date.strftime('%a')})
        except ValueError:
            break
    return days


def make_timetable(cfg, members, date):
    '''
    Generate a timetable in html with personal data of the assistent.
    Convert the genareted html to pdf and print the pdf file.
    '''
    if date == None:
        date = datetime.now().strftime("%m.%Y")
    with open('ass_timetable.html.j2') as _file:
        template = Template(_file.read())

    table_desc = [{ "name": "Tag", "length": "90", "id": "row_small" },
            { "name": "Begin", "length": "100", "id": "row_middle"},
            { "name": "Pause", "length": "80", "id": "row_middle"},
            { "name": "Ende", "length": "100", "id": "row_middle"},
            { "name": "Dauer", "length": "80", "id": "row_middle"},
            { "name": "*", "length": "20", "id": "row_small"},
            { "name": "Bemerkungen", "length": "150", "id": "row_large"}]
    print("make timetable")
    for assistant in members:
        rendered = template.render(
            name=f"{assistant['surename']} {assistant['name']}",
            date=date,
            days=generate_days(int(date.split('.')[1]), int(date.split('.')[0])),
            table_desc=table_desc
        )
        with open(f"{cfg['tmp_store_path']}/{assistant['name'].lower()}.html", "w") as _ofile:
            _ofile.write(rendered)
        _ofile.close()

        pdf_fqdn = f"{cfg['tmp_store_path']}/{assistant['name'].lower()}.pdf"
        html = HTML(f"{cfg['tmp_store_path']}/{assistant['name'].lower()}.html")
        html.render().write_pdf(pdf_fqdn)

        print(f"Printing timetable for {assistant['name']}")
        os.system(f"lpr -U fritschi {pdf_fqdn}")


def scan_timetable(cfg, scan_device):
    scan_device.__setattr__('source', 'Automatic Document Feeder(centrally aligned)')

    im = scan_device.scan()
    im.save(f"{cfg['tmp_store_path']}/{cfg['tmp_store_file']}")


def ocr_timetable(cfg, file):
    '''
    Get name of the assistent and date from the scaned timetable and return the result..
    '''

    t = pytesseract.image_to_string(Image.open(file), lang="deu", config="--oem 1")
    ocr_result = { 'date': '', 'ma': '' }

    #input("weiter")
    for line in t.split('\n'):
        if 'Mitarbeiter' in line:
            token = line.split(':')
            if len(token) > 2:
                idx = 0
                for e in token:
                    print(f"{idx}: {e}")
                    idx += 1
                idx=input("Select token: ")
                ocr_result['ma'] = line.split(':')[int(idx)].rstrip(' ').lstrip(' ')
            else:
                ocr_result['ma'] = line.split(':')[1].rstrip(' ').lstrip(' ')
        if 'Monat' in line:
            ocr_result['date'] = line.split(':')[1].rstrip(' ').lstrip(' ')
    pprint.pp(ocr_result)

    if ocr_result['date'] == '':
        ocr_result['date'] = input("Date is empty! Set correct date: ")


    return ocr_result


def move_timetable_to_perm(cfg, file, date: str, ass):
    '''
    Copy the timetable to the permanent storage.
    '''
 
    perm_path = f"{cfg['perm_store_path']}/{ass['surename'].lower()}{ass['name']}/stundennachweise"
    if os.path.isdir(perm_path):
        token = date.split('.')
        shutil.copy(file, f"{perm_path}/{token[1]}-{token[0]}.tif")
    else:
        print(f"Path={perm_path} not present!")



def make_summery_file(cfg, date, members: dict):
    '''

    '''
    try:
        cmd = f"convert -quality 50 -resize 30% -compress jpeg "
        token = date.split('.')
        for ass in members:
            cmd += f"{cfg['perm_store_path']}{ass['surename'].lower()}{ass['name']}/stundennachweise/{token[1]}-{token[0]}.tif "

        cmd += f" /tmp/stundennachweise.pdf"
        print(f"Run command: {cmd}")
        os.system(cmd)
    except OSError as _oserr:
        print(_oserr)
        return 1


def main():
    '''

    '''
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--print', type=str)
    parser.add_argument('-s', '--scan', action='store_true')
    parser.add_argument('-sf', '--summary', action='store_true')
    parser.add_argument('-d', '--date', type=str)
    args = parser.parse_args()

    perm_store_present = False
    try:
        with open("assistant.yml", "r") as _f:
            assistants = yaml.safe_load(_f)
        _f.close()
        with open("config.yml", "r") as _f:
            config = yaml.safe_load(_f)
        _f.close()
        if os.path.isdir(config['perm_store_path']):
            perm_store_present = True
        if not os.path.isdir(config['tmp_store_path']):
            print("Create temp working directory")
            os.makedirs(config['tmp_store_path'])
    except IOError as _ioerr:
        print(_ioerr)
        exit(1)

    if perm_store_present and args.scan and not args.summary:
        print(f"Intialing scanner device")
        scanner_device = None
        sane_ver = sane.init()
        for dev in sane.get_devices():
            if str(dev[0]).startswith('brother'):
                print(f"Open device {dev[0]}")
                scanner_device = sane.SaneDev(dev[0])
                scanner_device.__setattr__('resolution', 300)
        if scanner_device == None:
            print(f"Intialing scanner device failed!")
            return

        date = None
        iter = scanner_device.multi_scan()
        while True:
            try:
                tmp_image=iter.__next__()
                tmp_image.save(f"{config['tmp_store_path']}/{config['tmp_store_file']}")
                ocr_result = ocr_timetable(config, f"{config['tmp_store_path']}/{config['tmp_store_file']}")
                date = ocr_result['date']
                for assistant in assistants:
                    if ocr_result['ma'].split(' ')[1] == assistant['name']:
                        move_timetable_to_perm(
                            config,
                            f"{config['tmp_store_path']}/{config['tmp_store_file']}",
                            ocr_result['date'],
                            assistant)
                        break
                #input("next")
            except StopIteration:
                print(f"Document feeder is empty")
                break
        make_summery_file(config, date, assistants)
    elif args.summary and args.date:
        make_summery_file(config, args.date, assistants)

        return 1

    if args.date:
        date = args.date
    else:
        date = None

    if args.print and args.print.__eq__("all"):
        make_timetable(config, assistants, date)
    else:
        for assistant in assistants:
            if assistant['name'] == args.print:
                make_timetable(config, [assistant], date)
                break

    if config['tmp_store_cleanup']:
        print(f"Remove temp directory {config['tmp_store_path']}")
        shutil.rmtree(config['tmp_store_path'])

    return


if __name__ == "__main__":
    main()
