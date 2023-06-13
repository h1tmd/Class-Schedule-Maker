from flask import Flask, redirect, render_template, request, session
from flask_session import Session
from time import strftime, strptime
from copy import deepcopy

# Global
subjectparts = ["subname", "start", "end", "info"]
weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

# Configure application
app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


@app.route("/", methods=["GET", "POST"])
def home():
    # When form is submitted
    if request.method == "POST":
        # Check if user is editing a subject
        if request.form.get("subid") != "":
            existingid = int(request.form.get("subid"))
        else:
            existingid = None

        # Get subject data
        subject = {}
        for part in subjectparts:
            subject[part] = request.form.get(part)
        if strptime(subject["start"], "%H:%M") > strptime(subject["end"], "%H:%M"):
            message = "The end time is earlier than the starting time!"
            return render_template("error.html", message=message)
        subject["time"] = timestring(subject["start"], subject["end"])
        days = request.form.getlist("days")
        subject["days"] = days

        # Create session keys
        if "subjects" not in session:
            session["subjects"] = {}
        if "uniqueid" not in session:
            session["uniqueid"] = 0

        # Append to list
        for day in days:
            if day not in session["subjects"]:
                session["subjects"][day] = []

            # Check for collision
            if len(session["subjects"][day]) > 0:
                if ifcollision(
                    session["subjects"][day],
                    subject["start"],
                    subject["end"],
                    existingid,
                ):
                    message = "A class already exists in that spot!"
                    return render_template("error.html", message=message)

            subject["id"] = session["uniqueid"]
            session["subjects"][day].append(deepcopy(subject))
        session["uniqueid"] += 1

        # Delete old version of subject
        for day in session["subjects"]:
            for sub in session["subjects"][day]:
                if sub["id"] == existingid:
                    session["subjects"][day].remove(sub)

        # Update schedule
        session["timerange"] = settimerange(session["subjects"])
        for day in session["subjects"]:
            for sub in session["subjects"][day]:
                sub["grid"] = assigngridrows(
                    sub["start"], sub["end"], session["timerange"][0]
                )
                sub["grid"] += assigngridcol(day, list(session["subjects"].keys()))
        return redirect("/")

    # GET method
    if "subjects" in session:
        return render_template(
            "schedule.html",
            subjects=session["subjects"],
            timerange=session["timerange"],
            days=sorted(list(session["subjects"].keys()), key=weekdays.index),
        )
    else:
        return render_template("blank.html")


# Convert start and end time to HH:MM - HH:MM AM/PM
def timestring(start, end):
    start = strptime(start, "%H:%M")
    end = strptime(end, "%H:%M")
    string = strftime("%I:%M", start) + " - " + strftime("%I:%M %p", end)
    return string


# Check if a subject already exists in a time frame
def ifcollision(list, start, end, id):
    start = strptime(start, "%H:%M")
    end = strptime(end, "%H:%M")
    for sub in list:
        substart = strptime(sub["start"], "%H:%M")
        subend = strptime(sub["end"], "%H:%M")
        if sub["id"] == id:
            continue

        if start <= substart < end:
            return True
        elif start < subend <= end:
            return True
        elif substart <= start and end <= subend:
            return True
    return False


def assigngridcol(day, days):
    dayslist = sorted(days, key=weekdays.index)
    gridcol = {}
    for i in range(len(dayslist)):
        gridcol[dayslist[i]] = [i + 2, i + 3]
    return gridcol[day]


def assigngridrows(start, end, time):
    offset = 3
    starthour = int(start[:2])
    endhour = int(end[:2])
    startminute = int(start[-2:])
    endminute = int(end[-2:])
    sinc = 0
    einc = 0
    if startminute >= 25:
        sinc = 1
    elif startminute >= 50:
        sinc = 2
    if endminute >= 25:
        einc = 1
    elif endminute >= 50:
        einc = 2
    rowstart = 2 * starthour - 2 * time + offset + sinc
    rowend = 2 * endhour - 2 * time + offset + einc
    rows = [rowstart, rowend]
    return rows


# Assign time range based on earliest start time and latest end time
def settimerange(subs):
    earliest = strptime("23:59", "%H:%M")
    latest = strptime("00:00", "%H:%M")
    for day in subs.values():
        for sub in day:
            hour1 = strptime(sub["start"], "%H:%M")
            hour2 = strptime(sub["end"], "%H:%M")
            if hour1 < earliest:
                earliest = hour1
            if hour2 > latest:
                latest = hour2
    earliest = int(strftime("%H", earliest))
    latest = int(strftime("%H", latest))
    return (earliest, latest)
