"""Seed Orbit Chat demo: demo users with profile pictures + live discussions.

Run:  .venv/bin/python seed_chat_demo.py
Idempotent: skips users/rooms that already exist.
"""
import os
from datetime import timedelta

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "orbit_erp.settings")
django.setup()

from django.contrib.auth.models import User
from django.core.files import File
from django.utils import timezone

from core.models import Company, Membership, UserProfile
from orbitchat.models import ChatMember, ChatMessage, ChatReaction, ChatRoom

now = timezone.now()
AVATAR_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "media", "avatars", "demo")

DEMO_USERS = [
    # username, first, last, avatar file, title, role, company slugs
    ("selam.t", "Selam", "Tesfaye", "selam.jpg", "Operations Manager",
     "manager", ["heleph-coffee-group"]),
    ("dawit.h", "Dawit", "Haile", "dawit.jpg", "Logistics Coordinator",
     "manager", ["heleph-coffee-group", "abyssinia-freight-lines"]),
    ("meron.a", "Meron", "Assefa", "meron.jpg", "Finance Officer",
     "accountant", ["heleph-coffee-group"]),
    ("yonas.k", "Yonas", "Kebede", "yonas.jpg", "Driver Supervisor",
     "dispatcher", ["heleph-coffee-group", "abyssinia-freight-lines"]),
    ("hanna.g", "Hanna", "Girma", "hanna.jpg", "HR Manager",
     "manager", ["heleph-coffee-group"]),
    ("abebe.m", "Abebe", "Mulugeta", "abebe.jpg", "Warehouse Supervisor",
     "dispatcher", ["bean-power-coffee"]),
    ("tigist.r", "Tigist", "Redda", "tigist.jpg", "Export Documentation Specialist",
     "accountant", ["bean-power-coffee"]),
    ("samuel.d", "Samuel", "Demisse", "samuel.jpg", "IT Support Specialist",
     "viewer", ["heleph-coffee-group", "bean-power-coffee"]),
]

print("== demo users ==")
users = {}
for username, first, last, avatar_file, title, role, slugs in DEMO_USERS:
    u, created = User.objects.get_or_create(
        username=username,
        defaults={"first_name": first, "last_name": last,
                  "email": f"{username}@orbit.et", "is_active": True})
    if created:
        u.set_password("Demo@2026")
        u.save()
        print(f"  + user {username}")
    prof, _ = UserProfile.objects.get_or_create(user=u)
    prof.title = title
    apath = os.path.join(AVATAR_DIR, avatar_file)
    if os.path.exists(apath) and not prof.avatar:
        with open(apath, "rb") as f:
            prof.avatar.save(f"demo/{avatar_file}", File(f), save=True)
        print(f"  + avatar for {username}")
    prof.save()
    for slug in slugs:
        try:
            co = Company.objects.get(slug=slug)
        except Company.DoesNotExist:
            print(f"  ! company {slug} missing, skipped")
            continue
        Membership.objects.get_or_create(
            user=u, company=co, defaults={"role": role, "is_active": True})
    users[username] = u


def add_member(room, u, role="member"):
    ChatMember.objects.get_or_create(room=room, user=u,
                                     defaults={"role": role})


def post(room, company, sender, body, minutes_ago=0, reply_to=None):
    m = ChatMessage.objects.create(company=company, room=room, sender=sender,
                                   body=body, reply_to=reply_to)
    if minutes_ago:
        dt = now - timedelta(minutes=minutes_ago)
        ChatMessage.objects.filter(pk=m.pk).update(created_at=dt, updated_at=dt)
        m.created_at = dt
    return m


print("== demo discussions ==")
admins = list(User.objects.filter(is_superuser=True)[:1])

try:
    co = Company.objects.get(slug="heleph-coffee-group")
except Company.DoesNotExist:
    co = None

if co:
    # --- group: Operations Team discussion
    room, created = ChatRoom.objects.get_or_create(
        company=co, room_type="group", name="Operations Team",
        defaults={"description": "Daily operations coordination",
                  "created_by": users["selam.t"]})
    if created:
        for un in ["selam.t", "dawit.h", "yonas.k", "hanna.g", "samuel.d"]:
            add_member(room, users[un])
        add_member(room, users["selam.t"], "admin")
        for a in admins:
            add_member(room, a)
        s, d, y, h = users["selam.t"], users["dawit.h"], users["yonas.k"], users["hanna.g"]
        m1 = post(room, co, s, "Good morning team! Quick sync on today's dispatches — we have 6 trucks scheduled.", 180)
        m2 = post(room, co, d, "Morning! 4 are already loaded at the Addis warehouse. 2 more loading now.", 172, reply_to=m1)
        m3 = post(room, co, y, "Drivers are briefed. @dawit.h the Djibouti route papers — are they ready?", 165)
        m4 = post(room, co, d, "Yes, customs docs cleared yesterday. I'll share the copies here.", 158, reply_to=m3)
        m5 = post(room, co, s, "Excellent. Fuel advance requests for the long-haul trips are approved.", 140)
        m6 = post(room, co, h, "Reminder: driver medical renewals are due next week. I'll send the list.", 120)
        m7 = post(room, co, d, "Noted. Also the new GPS trackers arrived — @samuel.d can you help install the app on the drivers' phones?", 95)
        m8 = post(room, co, users["samuel.d"], "Sure thing! I'll be at the depot at 2 PM with everything ready.", 88, reply_to=m7)
        m9 = post(room, co, s, "Perfect. Let's keep the updates coming here throughout the day.", 60)
        m10 = post(room, co, y, "Truck ET-4521 just left the gate. ETA Djibouti corridor by evening.", 25)
        ChatReaction.objects.get_or_create(message=m2, user=s, reaction="like")
        ChatReaction.objects.get_or_create(message=m2, user=y, reaction="like")
        ChatReaction.objects.get_or_create(message=m5, user=d, reaction="love")
        ChatReaction.objects.get_or_create(message=m8, user=s, reaction="like")
        print(f"  + group 'Operations Team' with 10 messages")

    # --- DM: Selam <-> Dawit
    dm, created = ChatRoom.objects.get_or_create(
        company=co, room_type="dm",
        defaults={"created_by": users["selam.t"]})
    if created:
        add_member(dm, users["selam.t"], "admin")
        add_member(dm, users["dawit.h"])
        for a in admins:
            add_member(dm, a)
        s, d = users["selam.t"], users["dawit.h"]
        post(dm, co, s, "Hi Dawit, do we have the signed delivery note for order #1042?", 300)
        post(dm, co, d, "Hi Selam! Yes, the client signed it this morning. Uploading the scan now.", 290)
        post(dm, co, s, "Great, finance needs it to release the invoice.", 285)
        post(dm, co, d, "Done — it's attached to the delivery record in the system.", 270)
        post(dm, co, s, "Perfect, thank you!", 265)
        print("  + DM Selam <-> Dawit with 5 messages")

try:
    co2 = Company.objects.get(slug="bean-power-coffee")
except Company.DoesNotExist:
    co2 = None

if co2:
    room, created = ChatRoom.objects.get_or_create(
        company=co2, room_type="group", name="Export Desk",
        defaults={"description": "Coffee export coordination",
                  "created_by": users["tigist.r"]})
    if created:
        for un in ["tigist.r", "abebe.m", "samuel.d"]:
            add_member(room, users[un])
        add_member(room, users["tigist.r"], "admin")
        for a2 in admins:
            add_member(room, a2)
        t, a = users["tigist.r"], users["abebe.m"]
        m1 = post(room, co2, t, "The Hamburg shipment documents are ready — bill of lading, ICO marks, and phytosanitary certificate.", 200)
        m2 = post(room, co2, a, "Warehouse confirms 275 bags loaded and sealed. Container number MSKU-884120.", 190, reply_to=m1)
        m3 = post(room, co2, t, "Excellent! @abebe.m please share the container seal photos.", 180)
        m4 = post(room, co2, a, "Uploading now — seal intact, photos attached to the shipment record.", 170)
        m5 = post(room, co2, t, "Customs declaration submitted. Vessel departs Thursday.", 150)
        ChatReaction.objects.get_or_create(message=m2, user=t, reaction="love")
        ChatReaction.objects.get_or_create(message=m5, user=a, reaction="like")
        print("  + group 'Export Desk' with 5 messages")

print("done.")
