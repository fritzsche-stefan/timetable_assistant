# timetable_assistant

This is a small python script to do some management chore for my caregivers. The current version
is a first shot and i know there are many things that cloud be done better. Maybe someday ...

Your support is welcome.


The script can do the following tasks.

- generate a personally, empty monthly timetable for the caregivers.
- scan and process the filled out timetables
  - scan with installed device (in my case it is brother scanner and printer)
  - make OCR processing for every scanned image
  - store the image in the configured archive store
  - generate a summary pdf file (all scanned images in one pdf)

## Run the script 

Use -s to scan timetables
```
> python3 timetable_assistant.py -s
```


Use -p to print timetables

- all configured caregivers
```
> python3 timetable_assistant.py -p all
```

- only for the given name
```
> python3 timetable_assistant.py -p Mustermann
```



