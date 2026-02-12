"""
Domain-Agnostic Training Data Generator
Generates training samples for ANY domain/project type
"""
import json
import random
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class DomainEntity:
    """Represents an entity in a domain"""
    name: str  # e.g., "Patient", "Course", "Property"
    plural: str  # e.g., "Patients", "Courses", "Properties"
    attributes: List[Tuple[str, str]]  # [(name, type), ...]
    relationships: List[str]  # Related entities


# ============================================================================
# DOMAIN DEFINITIONS - Covering 20+ different project domains
# ============================================================================

DOMAINS = {
    # Healthcare
    "healthcare": {
        "name": "Healthcare Management System",
        "entities": [
            DomainEntity(
                name="Patient",
                plural="Patients",
                attributes=[
                    ("name", "string"), ("email", "string"), ("phone", "string"),
                    ("dateOfBirth", "date"), ("bloodGroup", "string"), ("medicalHistory", "text"),
                    ("insuranceNumber", "string"), ("emergencyContact", "string")
                ],
                relationships=["Doctor", "Appointment", "MedicalRecord", "Prescription"]
            ),
            DomainEntity(
                name="Doctor",
                plural="Doctors",
                attributes=[
                    ("name", "string"), ("email", "string"), ("specialization", "string"),
                    ("licenseNumber", "string"), ("experience", "number"), ("consultationFee", "decimal"),
                    ("availability", "json"), ("rating", "decimal")
                ],
                relationships=["Patient", "Appointment", "Department"]
            ),
            DomainEntity(
                name="Appointment",
                plural="Appointments",
                attributes=[
                    ("scheduledAt", "datetime"), ("status", "enum:scheduled,completed,cancelled"),
                    ("type", "enum:consultation,followup,emergency"), ("notes", "text"),
                    ("duration", "number"), ("symptoms", "text")
                ],
                relationships=["Patient", "Doctor"]
            ),
            DomainEntity(
                name="Prescription",
                plural="Prescriptions",
                attributes=[
                    ("medications", "json"), ("dosage", "text"), ("instructions", "text"),
                    ("validUntil", "date"), ("refillsAllowed", "number")
                ],
                relationships=["Patient", "Doctor", "Appointment"]
            ),
        ],
        "features": ["appointment booking", "medical records", "prescription management", "billing", "lab reports"]
    },

    # Education / E-Learning
    "education": {
        "name": "E-Learning Platform",
        "entities": [
            DomainEntity(
                name="Student",
                plural="Students",
                attributes=[
                    ("name", "string"), ("email", "string"), ("enrollmentNumber", "string"),
                    ("grade", "string"), ("enrollmentDate", "date"), ("guardianContact", "string")
                ],
                relationships=["Course", "Enrollment", "Assignment", "Grade"]
            ),
            DomainEntity(
                name="Course",
                plural="Courses",
                attributes=[
                    ("title", "string"), ("description", "text"), ("duration", "number"),
                    ("level", "enum:beginner,intermediate,advanced"), ("price", "decimal"),
                    ("thumbnail", "string"), ("syllabus", "json"), ("isPublished", "boolean")
                ],
                relationships=["Instructor", "Student", "Module", "Quiz"]
            ),
            DomainEntity(
                name="Instructor",
                plural="Instructors",
                attributes=[
                    ("name", "string"), ("email", "string"), ("bio", "text"),
                    ("expertise", "json"), ("rating", "decimal"), ("totalStudents", "number")
                ],
                relationships=["Course"]
            ),
            DomainEntity(
                name="Enrollment",
                plural="Enrollments",
                attributes=[
                    ("enrolledAt", "datetime"), ("progress", "number"), ("status", "enum:active,completed,dropped"),
                    ("completedAt", "datetime"), ("certificateUrl", "string")
                ],
                relationships=["Student", "Course"]
            ),
            DomainEntity(
                name="Quiz",
                plural="Quizzes",
                attributes=[
                    ("title", "string"), ("questions", "json"), ("duration", "number"),
                    ("passingScore", "number"), ("maxAttempts", "number")
                ],
                relationships=["Course", "Module"]
            ),
        ],
        "features": ["course enrollment", "video lectures", "quizzes", "progress tracking", "certificates", "discussion forums"]
    },

    # Real Estate
    "real_estate": {
        "name": "Real Estate Platform",
        "entities": [
            DomainEntity(
                name="Property",
                plural="Properties",
                attributes=[
                    ("title", "string"), ("description", "text"), ("price", "decimal"),
                    ("type", "enum:apartment,house,villa,land,commercial"), ("status", "enum:available,sold,rented"),
                    ("bedrooms", "number"), ("bathrooms", "number"), ("area", "decimal"),
                    ("address", "string"), ("city", "string"), ("coordinates", "json"),
                    ("amenities", "json"), ("images", "json"), ("virtualTourUrl", "string")
                ],
                relationships=["Agent", "Owner", "Inquiry"]
            ),
            DomainEntity(
                name="Agent",
                plural="Agents",
                attributes=[
                    ("name", "string"), ("email", "string"), ("phone", "string"),
                    ("licenseNumber", "string"), ("commission", "decimal"), ("rating", "decimal"),
                    ("specialization", "json"), ("propertiesSold", "number")
                ],
                relationships=["Property", "Client"]
            ),
            DomainEntity(
                name="Inquiry",
                plural="Inquiries",
                attributes=[
                    ("message", "text"), ("status", "enum:new,contacted,scheduled,closed"),
                    ("preferredContactTime", "string"), ("budget", "decimal")
                ],
                relationships=["Property", "Client", "Agent"]
            ),
            DomainEntity(
                name="Booking",
                plural="Bookings",
                attributes=[
                    ("visitDate", "datetime"), ("status", "enum:scheduled,completed,cancelled"),
                    ("feedback", "text"), ("rating", "number")
                ],
                relationships=["Property", "Client", "Agent"]
            ),
        ],
        "features": ["property listings", "virtual tours", "appointment scheduling", "mortgage calculator", "agent matching"]
    },

    # HR / Recruitment
    "hr_recruitment": {
        "name": "HR & Recruitment System",
        "entities": [
            DomainEntity(
                name="Employee",
                plural="Employees",
                attributes=[
                    ("name", "string"), ("email", "string"), ("employeeId", "string"),
                    ("designation", "string"), ("department", "string"), ("joiningDate", "date"),
                    ("salary", "decimal"), ("manager", "uuid"), ("skills", "json"),
                    ("address", "text"), ("bankDetails", "json")
                ],
                relationships=["Department", "Leave", "Payroll", "Performance"]
            ),
            DomainEntity(
                name="JobPosting",
                plural="JobPostings",
                attributes=[
                    ("title", "string"), ("description", "text"), ("requirements", "json"),
                    ("salary", "json"), ("location", "string"), ("type", "enum:fulltime,parttime,contract,internship"),
                    ("experience", "string"), ("deadline", "date"), ("isActive", "boolean")
                ],
                relationships=["Department", "Application"]
            ),
            DomainEntity(
                name="Application",
                plural="Applications",
                attributes=[
                    ("resumeUrl", "string"), ("coverLetter", "text"), ("status", "enum:applied,screening,interview,offered,rejected"),
                    ("appliedAt", "datetime"), ("notes", "text"), ("interviewSchedule", "json")
                ],
                relationships=["JobPosting", "Candidate"]
            ),
            DomainEntity(
                name="Leave",
                plural="Leaves",
                attributes=[
                    ("type", "enum:sick,casual,earned,maternity,paternity"), ("startDate", "date"),
                    ("endDate", "date"), ("reason", "text"), ("status", "enum:pending,approved,rejected"),
                    ("approvedBy", "uuid")
                ],
                relationships=["Employee"]
            ),
            DomainEntity(
                name="Attendance",
                plural="Attendances",
                attributes=[
                    ("date", "date"), ("checkIn", "datetime"), ("checkOut", "datetime"),
                    ("status", "enum:present,absent,halfday,wfh"), ("overtime", "number")
                ],
                relationships=["Employee"]
            ),
        ],
        "features": ["job posting", "application tracking", "interview scheduling", "leave management", "payroll", "performance review"]
    },

    # Restaurant / Food Delivery
    "restaurant": {
        "name": "Restaurant & Food Delivery",
        "entities": [
            DomainEntity(
                name="Restaurant",
                plural="Restaurants",
                attributes=[
                    ("name", "string"), ("description", "text"), ("cuisine", "json"),
                    ("address", "string"), ("coordinates", "json"), ("rating", "decimal"),
                    ("priceRange", "enum:budget,moderate,expensive"), ("openingHours", "json"),
                    ("images", "json"), ("isOpen", "boolean"), ("deliveryRadius", "number")
                ],
                relationships=["Menu", "Order", "Review"]
            ),
            DomainEntity(
                name="MenuItem",
                plural="MenuItems",
                attributes=[
                    ("name", "string"), ("description", "text"), ("price", "decimal"),
                    ("category", "string"), ("image", "string"), ("isVeg", "boolean"),
                    ("spiceLevel", "enum:mild,medium,hot"), ("isAvailable", "boolean"),
                    ("preparationTime", "number"), ("nutritionInfo", "json")
                ],
                relationships=["Restaurant", "OrderItem"]
            ),
            DomainEntity(
                name="Order",
                plural="Orders",
                attributes=[
                    ("orderNumber", "string"), ("status", "enum:placed,confirmed,preparing,ready,delivered,cancelled"),
                    ("totalAmount", "decimal"), ("deliveryAddress", "text"), ("deliveryInstructions", "text"),
                    ("paymentMethod", "enum:card,upi,cod"), ("paymentStatus", "enum:pending,paid,refunded"),
                    ("estimatedDelivery", "datetime")
                ],
                relationships=["Customer", "Restaurant", "DeliveryAgent"]
            ),
            DomainEntity(
                name="DeliveryAgent",
                plural="DeliveryAgents",
                attributes=[
                    ("name", "string"), ("phone", "string"), ("vehicleNumber", "string"),
                    ("currentLocation", "json"), ("isAvailable", "boolean"), ("rating", "decimal"),
                    ("totalDeliveries", "number")
                ],
                relationships=["Order"]
            ),
        ],
        "features": ["menu management", "order tracking", "live delivery tracking", "reviews", "coupons", "loyalty points"]
    },

    # Finance / Banking
    "finance": {
        "name": "Banking & Finance App",
        "entities": [
            DomainEntity(
                name="Account",
                plural="Accounts",
                attributes=[
                    ("accountNumber", "string"), ("type", "enum:savings,current,fixed,recurring"),
                    ("balance", "decimal"), ("currency", "string"), ("status", "enum:active,frozen,closed"),
                    ("interestRate", "decimal"), ("openedAt", "date"), ("branch", "string")
                ],
                relationships=["Customer", "Transaction", "Card"]
            ),
            DomainEntity(
                name="Transaction",
                plural="Transactions",
                attributes=[
                    ("transactionId", "string"), ("type", "enum:credit,debit,transfer"),
                    ("amount", "decimal"), ("description", "text"), ("category", "string"),
                    ("status", "enum:pending,completed,failed,reversed"), ("timestamp", "datetime"),
                    ("referenceNumber", "string")
                ],
                relationships=["Account"]
            ),
            DomainEntity(
                name="Loan",
                plural="Loans",
                attributes=[
                    ("loanNumber", "string"), ("type", "enum:personal,home,car,education,business"),
                    ("principal", "decimal"), ("interestRate", "decimal"), ("tenure", "number"),
                    ("emi", "decimal"), ("status", "enum:applied,approved,disbursed,closed"),
                    ("disbursedAt", "date"), ("nextEmiDate", "date")
                ],
                relationships=["Customer", "Account"]
            ),
            DomainEntity(
                name="Card",
                plural="Cards",
                attributes=[
                    ("cardNumber", "string"), ("type", "enum:debit,credit"), ("variant", "string"),
                    ("expiryDate", "date"), ("cvv", "string"), ("limit", "decimal"),
                    ("status", "enum:active,blocked,expired"), ("pin", "string")
                ],
                relationships=["Account", "Transaction"]
            ),
        ],
        "features": ["fund transfer", "bill payment", "loan application", "investment", "budget tracking", "statements"]
    },

    # Logistics / Shipping
    "logistics": {
        "name": "Logistics & Shipping Platform",
        "entities": [
            DomainEntity(
                name="Shipment",
                plural="Shipments",
                attributes=[
                    ("trackingNumber", "string"), ("status", "enum:booked,picked,intransit,outfordelivery,delivered"),
                    ("origin", "json"), ("destination", "json"), ("weight", "decimal"),
                    ("dimensions", "json"), ("type", "enum:standard,express,overnight"),
                    ("estimatedDelivery", "date"), ("actualDelivery", "date"), ("cost", "decimal")
                ],
                relationships=["Sender", "Receiver", "Driver", "Warehouse"]
            ),
            DomainEntity(
                name="Warehouse",
                plural="Warehouses",
                attributes=[
                    ("name", "string"), ("address", "text"), ("coordinates", "json"),
                    ("capacity", "number"), ("currentOccupancy", "number"), ("type", "enum:hub,spoke,fulfillment"),
                    ("operatingHours", "json")
                ],
                relationships=["Shipment", "Inventory"]
            ),
            DomainEntity(
                name="Vehicle",
                plural="Vehicles",
                attributes=[
                    ("vehicleNumber", "string"), ("type", "enum:bike,van,truck,container"),
                    ("capacity", "decimal"), ("currentLocation", "json"), ("status", "enum:available,intransit,maintenance"),
                    ("fuelType", "string"), ("lastService", "date")
                ],
                relationships=["Driver", "Shipment"]
            ),
            DomainEntity(
                name="Driver",
                plural="Drivers",
                attributes=[
                    ("name", "string"), ("phone", "string"), ("licenseNumber", "string"),
                    ("currentLocation", "json"), ("status", "enum:available,onduty,offline"),
                    ("rating", "decimal"), ("totalDeliveries", "number")
                ],
                relationships=["Vehicle", "Shipment"]
            ),
        ],
        "features": ["shipment tracking", "route optimization", "warehouse management", "fleet management", "proof of delivery"]
    },

    # Event Management
    "events": {
        "name": "Event Management Platform",
        "entities": [
            DomainEntity(
                name="Event",
                plural="Events",
                attributes=[
                    ("title", "string"), ("description", "text"), ("type", "enum:conference,workshop,concert,wedding,corporate"),
                    ("startDate", "datetime"), ("endDate", "datetime"), ("venue", "string"),
                    ("capacity", "number"), ("ticketPrice", "decimal"), ("status", "enum:draft,published,ongoing,completed,cancelled"),
                    ("banner", "string"), ("organizer", "uuid")
                ],
                relationships=["Venue", "Ticket", "Speaker", "Sponsor"]
            ),
            DomainEntity(
                name="Ticket",
                plural="Tickets",
                attributes=[
                    ("ticketNumber", "string"), ("type", "enum:general,vip,early_bird"),
                    ("price", "decimal"), ("status", "enum:booked,checked_in,cancelled"),
                    ("purchasedAt", "datetime"), ("qrCode", "string")
                ],
                relationships=["Event", "Attendee"]
            ),
            DomainEntity(
                name="Venue",
                plural="Venues",
                attributes=[
                    ("name", "string"), ("address", "text"), ("capacity", "number"),
                    ("amenities", "json"), ("pricePerHour", "decimal"), ("images", "json"),
                    ("contactPerson", "string"), ("contactPhone", "string")
                ],
                relationships=["Event"]
            ),
            DomainEntity(
                name="Attendee",
                plural="Attendees",
                attributes=[
                    ("name", "string"), ("email", "string"), ("phone", "string"),
                    ("dietaryPreference", "string"), ("specialRequirements", "text"),
                    ("checkedInAt", "datetime")
                ],
                relationships=["Event", "Ticket"]
            ),
        ],
        "features": ["event creation", "ticket booking", "check-in", "attendee management", "live streaming", "feedback"]
    },

    # Social Media
    "social_media": {
        "name": "Social Media Platform",
        "entities": [
            DomainEntity(
                name="User",
                plural="Users",
                attributes=[
                    ("username", "string"), ("email", "string"), ("bio", "text"),
                    ("avatarUrl", "string"), ("coverUrl", "string"), ("isVerified", "boolean"),
                    ("followers", "number"), ("following", "number"), ("postsCount", "number"),
                    ("isPrivate", "boolean")
                ],
                relationships=["Post", "Story", "Message"]
            ),
            DomainEntity(
                name="Post",
                plural="Posts",
                attributes=[
                    ("content", "text"), ("media", "json"), ("likes", "number"),
                    ("comments", "number"), ("shares", "number"), ("visibility", "enum:public,friends,private"),
                    ("location", "string"), ("hashtags", "json"), ("mentions", "json")
                ],
                relationships=["User", "Comment"]
            ),
            DomainEntity(
                name="Story",
                plural="Stories",
                attributes=[
                    ("mediaUrl", "string"), ("mediaType", "enum:image,video"),
                    ("views", "number"), ("expiresAt", "datetime"), ("reactions", "json")
                ],
                relationships=["User"]
            ),
            DomainEntity(
                name="Message",
                plural="Messages",
                attributes=[
                    ("content", "text"), ("mediaUrl", "string"), ("isRead", "boolean"),
                    ("sentAt", "datetime"), ("readAt", "datetime"), ("isDeleted", "boolean")
                ],
                relationships=["User", "Conversation"]
            ),
        ],
        "features": ["post creation", "stories", "direct messaging", "notifications", "search", "trending", "live streaming"]
    },

    # Inventory Management
    "inventory": {
        "name": "Inventory Management System",
        "entities": [
            DomainEntity(
                name="Product",
                plural="Products",
                attributes=[
                    ("name", "string"), ("sku", "string"), ("barcode", "string"),
                    ("description", "text"), ("category", "string"), ("unit", "string"),
                    ("costPrice", "decimal"), ("sellingPrice", "decimal"), ("minStock", "number"),
                    ("maxStock", "number"), ("reorderPoint", "number")
                ],
                relationships=["Category", "Supplier", "StockMovement"]
            ),
            DomainEntity(
                name="StockMovement",
                plural="StockMovements",
                attributes=[
                    ("type", "enum:purchase,sale,adjustment,transfer,return"),
                    ("quantity", "number"), ("unitPrice", "decimal"), ("totalAmount", "decimal"),
                    ("reference", "string"), ("notes", "text"), ("timestamp", "datetime")
                ],
                relationships=["Product", "Warehouse"]
            ),
            DomainEntity(
                name="PurchaseOrder",
                plural="PurchaseOrders",
                attributes=[
                    ("orderNumber", "string"), ("status", "enum:draft,submitted,approved,received,cancelled"),
                    ("totalAmount", "decimal"), ("expectedDate", "date"), ("receivedDate", "date"),
                    ("notes", "text")
                ],
                relationships=["Supplier", "Product"]
            ),
            DomainEntity(
                name="Supplier",
                plural="Suppliers",
                attributes=[
                    ("name", "string"), ("email", "string"), ("phone", "string"),
                    ("address", "text"), ("gstNumber", "string"), ("paymentTerms", "string"),
                    ("rating", "decimal")
                ],
                relationships=["Product", "PurchaseOrder"]
            ),
        ],
        "features": ["stock tracking", "purchase orders", "stock alerts", "barcode scanning", "reports", "multi-warehouse"]
    },

    # Fitness / Gym
    "fitness": {
        "name": "Fitness & Gym Management",
        "entities": [
            DomainEntity(
                name="Member",
                plural="Members",
                attributes=[
                    ("name", "string"), ("email", "string"), ("phone", "string"),
                    ("membershipType", "enum:basic,premium,vip"), ("startDate", "date"),
                    ("endDate", "date"), ("height", "decimal"), ("weight", "decimal"),
                    ("fitnessGoal", "string"), ("emergencyContact", "string")
                ],
                relationships=["Membership", "Workout", "Trainer"]
            ),
            DomainEntity(
                name="Trainer",
                plural="Trainers",
                attributes=[
                    ("name", "string"), ("email", "string"), ("specialization", "json"),
                    ("certification", "json"), ("experience", "number"), ("rating", "decimal"),
                    ("hourlyRate", "decimal"), ("availability", "json")
                ],
                relationships=["Member", "Session"]
            ),
            DomainEntity(
                name="Workout",
                plural="Workouts",
                attributes=[
                    ("name", "string"), ("description", "text"), ("type", "enum:cardio,strength,flexibility,hiit"),
                    ("duration", "number"), ("caloriesBurned", "number"), ("difficulty", "enum:beginner,intermediate,advanced"),
                    ("exercises", "json"), ("videoUrl", "string")
                ],
                relationships=["Member", "Trainer"]
            ),
            DomainEntity(
                name="Session",
                plural="Sessions",
                attributes=[
                    ("scheduledAt", "datetime"), ("duration", "number"), ("status", "enum:scheduled,completed,cancelled"),
                    ("type", "enum:personal,group,online"), ("notes", "text"), ("feedback", "text")
                ],
                relationships=["Member", "Trainer"]
            ),
        ],
        "features": ["membership management", "workout plans", "trainer booking", "progress tracking", "diet plans", "equipment booking"]
    },

    # Travel / Booking
    "travel": {
        "name": "Travel & Booking Platform",
        "entities": [
            DomainEntity(
                name="Flight",
                plural="Flights",
                attributes=[
                    ("flightNumber", "string"), ("airline", "string"), ("origin", "string"),
                    ("destination", "string"), ("departureTime", "datetime"), ("arrivalTime", "datetime"),
                    ("price", "decimal"), ("seatsAvailable", "number"), ("class", "enum:economy,business,first"),
                    ("status", "enum:scheduled,delayed,cancelled,boarding,departed")
                ],
                relationships=["Booking", "Airport"]
            ),
            DomainEntity(
                name="Hotel",
                plural="Hotels",
                attributes=[
                    ("name", "string"), ("description", "text"), ("address", "text"),
                    ("starRating", "number"), ("amenities", "json"), ("images", "json"),
                    ("pricePerNight", "decimal"), ("checkInTime", "string"), ("checkOutTime", "string"),
                    ("coordinates", "json")
                ],
                relationships=["Room", "Booking", "Review"]
            ),
            DomainEntity(
                name="Booking",
                plural="Bookings",
                attributes=[
                    ("bookingNumber", "string"), ("type", "enum:flight,hotel,package"),
                    ("status", "enum:pending,confirmed,cancelled,completed"), ("totalAmount", "decimal"),
                    ("checkIn", "date"), ("checkOut", "date"), ("guests", "number"),
                    ("specialRequests", "text"), ("paymentStatus", "enum:pending,paid,refunded")
                ],
                relationships=["Customer", "Flight", "Hotel"]
            ),
            DomainEntity(
                name="Package",
                plural="Packages",
                attributes=[
                    ("name", "string"), ("description", "text"), ("duration", "number"),
                    ("destinations", "json"), ("inclusions", "json"), ("price", "decimal"),
                    ("maxGroupSize", "number"), ("itinerary", "json")
                ],
                relationships=["Booking"]
            ),
        ],
        "features": ["flight search", "hotel booking", "package tours", "itinerary planning", "reviews", "loyalty points"]
    },

    # Project Management
    "project_management": {
        "name": "Project Management Tool",
        "entities": [
            DomainEntity(
                name="Project",
                plural="Projects",
                attributes=[
                    ("name", "string"), ("description", "text"), ("status", "enum:planning,active,onhold,completed"),
                    ("startDate", "date"), ("endDate", "date"), ("budget", "decimal"),
                    ("priority", "enum:low,medium,high,critical"), ("progress", "number"),
                    ("visibility", "enum:private,team,public")
                ],
                relationships=["Team", "Task", "Milestone"]
            ),
            DomainEntity(
                name="Task",
                plural="Tasks",
                attributes=[
                    ("title", "string"), ("description", "text"), ("status", "enum:todo,inprogress,review,done"),
                    ("priority", "enum:low,medium,high,critical"), ("dueDate", "date"),
                    ("estimatedHours", "number"), ("actualHours", "number"), ("labels", "json")
                ],
                relationships=["Project", "Assignee", "Comment"]
            ),
            DomainEntity(
                name="Sprint",
                plural="Sprints",
                attributes=[
                    ("name", "string"), ("goal", "text"), ("startDate", "date"),
                    ("endDate", "date"), ("status", "enum:planning,active,completed"),
                    ("velocity", "number")
                ],
                relationships=["Project", "Task"]
            ),
            DomainEntity(
                name="TimeEntry",
                plural="TimeEntries",
                attributes=[
                    ("description", "text"), ("startTime", "datetime"), ("endTime", "datetime"),
                    ("duration", "number"), ("billable", "boolean"), ("hourlyRate", "decimal")
                ],
                relationships=["Task", "User"]
            ),
        ],
        "features": ["kanban board", "sprint planning", "time tracking", "gantt chart", "team collaboration", "reports"]
    },

    # CRM
    "crm": {
        "name": "Customer Relationship Management",
        "entities": [
            DomainEntity(
                name="Lead",
                plural="Leads",
                attributes=[
                    ("name", "string"), ("email", "string"), ("phone", "string"),
                    ("company", "string"), ("source", "enum:website,referral,social,advertisement"),
                    ("status", "enum:new,contacted,qualified,proposal,negotiation,won,lost"),
                    ("value", "decimal"), ("notes", "text")
                ],
                relationships=["Contact", "Deal", "Activity"]
            ),
            DomainEntity(
                name="Contact",
                plural="Contacts",
                attributes=[
                    ("name", "string"), ("email", "string"), ("phone", "string"),
                    ("designation", "string"), ("company", "string"), ("address", "text"),
                    ("tags", "json"), ("socialLinks", "json")
                ],
                relationships=["Lead", "Deal", "Note"]
            ),
            DomainEntity(
                name="Deal",
                plural="Deals",
                attributes=[
                    ("title", "string"), ("value", "decimal"), ("stage", "enum:prospecting,qualification,proposal,negotiation,closed"),
                    ("probability", "number"), ("expectedCloseDate", "date"), ("actualCloseDate", "date"),
                    ("notes", "text")
                ],
                relationships=["Contact", "Lead", "Activity"]
            ),
            DomainEntity(
                name="Activity",
                plural="Activities",
                attributes=[
                    ("type", "enum:call,email,meeting,task,note"),
                    ("subject", "string"), ("description", "text"), ("scheduledAt", "datetime"),
                    ("completedAt", "datetime"), ("outcome", "text")
                ],
                relationships=["Lead", "Contact", "Deal"]
            ),
        ],
        "features": ["lead tracking", "deal pipeline", "email integration", "call logging", "reports", "automation"]
    },

    # Subscription / SaaS
    "subscription": {
        "name": "SaaS Subscription Platform",
        "entities": [
            DomainEntity(
                name="Plan",
                plural="Plans",
                attributes=[
                    ("name", "string"), ("description", "text"), ("price", "decimal"),
                    ("billingCycle", "enum:monthly,quarterly,yearly"), ("features", "json"),
                    ("limits", "json"), ("trialDays", "number"), ("isActive", "boolean")
                ],
                relationships=["Subscription"]
            ),
            DomainEntity(
                name="Subscription",
                plural="Subscriptions",
                attributes=[
                    ("status", "enum:trialing,active,past_due,cancelled,expired"),
                    ("startDate", "date"), ("endDate", "date"), ("trialEndDate", "date"),
                    ("autoRenew", "boolean"), ("cancelledAt", "datetime"), ("cancelReason", "text")
                ],
                relationships=["Customer", "Plan", "Invoice"]
            ),
            DomainEntity(
                name="Invoice",
                plural="Invoices",
                attributes=[
                    ("invoiceNumber", "string"), ("amount", "decimal"), ("tax", "decimal"),
                    ("status", "enum:draft,pending,paid,overdue,cancelled"), ("dueDate", "date"),
                    ("paidAt", "datetime"), ("paymentMethod", "string")
                ],
                relationships=["Subscription", "Customer"]
            ),
            DomainEntity(
                name="Usage",
                plural="Usages",
                attributes=[
                    ("metric", "string"), ("quantity", "number"), ("timestamp", "datetime"),
                    ("billable", "boolean")
                ],
                relationships=["Subscription"]
            ),
        ],
        "features": ["plan management", "billing", "usage tracking", "invoicing", "payment processing", "analytics"]
    },
}


# ============================================================================
# CODE GENERATION TEMPLATES
# ============================================================================

def generate_react_component(entity: DomainEntity, domain_name: str) -> str:
    """Generate React component for an entity"""
    attrs = entity.attributes[:6]  # Take first 6 attributes

    form_fields = []
    for attr_name, attr_type in attrs:
        if attr_type == "string":
            form_fields.append(f'''
        <div>
          <label htmlFor="{attr_name}" className="block text-sm font-medium text-gray-700 mb-1">
            {attr_name.replace('_', ' ').title()}
          </label>
          <input
            {{...register('{attr_name}')}}
            type="text"
            id="{attr_name}"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          {{errors.{attr_name} && (
            <p className="mt-1 text-sm text-red-600">{{errors.{attr_name}.message}}</p>
          )}}
        </div>''')
        elif attr_type == "text":
            form_fields.append(f'''
        <div>
          <label htmlFor="{attr_name}" className="block text-sm font-medium text-gray-700 mb-1">
            {attr_name.replace('_', ' ').title()}
          </label>
          <textarea
            {{...register('{attr_name}')}}
            id="{attr_name}"
            rows={{4}}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>''')
        elif attr_type == "decimal" or attr_type == "number":
            form_fields.append(f'''
        <div>
          <label htmlFor="{attr_name}" className="block text-sm font-medium text-gray-700 mb-1">
            {attr_name.replace('_', ' ').title()}
          </label>
          <input
            {{...register('{attr_name}', {{ valueAsNumber: true }})}}
            type="number"
            id="{attr_name}"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>''')
        elif attr_type.startswith("enum:"):
            options = attr_type.replace("enum:", "").split(",")
            options_jsx = "\n".join([f'            <option value="{opt}">{opt.replace("_", " ").title()}</option>' for opt in options])
            form_fields.append(f'''
        <div>
          <label htmlFor="{attr_name}" className="block text-sm font-medium text-gray-700 mb-1">
            {attr_name.replace('_', ' ').title()}
          </label>
          <select
            {{...register('{attr_name}')}}
            id="{attr_name}"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
{options_jsx}
          </select>
        </div>''')

    return f'''```tsx
import React from 'react';
import {{ useForm }} from 'react-hook-form';
import {{ zodResolver }} from '@hookform/resolvers/zod';
import {{ z }} from 'zod';
import {{ Loader2 }} from 'lucide-react';

const {entity.name.lower()}Schema = z.object({{
{chr(10).join([f"  {attr[0]}: z.{'string()' if attr[1] in ['string', 'text'] else 'number()' if attr[1] in ['number', 'decimal'] else 'string()'}," for attr in attrs])}
}});

type {entity.name}FormData = z.infer<typeof {entity.name.lower()}Schema>;

interface {entity.name}FormProps {{
  onSubmit: (data: {entity.name}FormData) => Promise<void>;
  initialData?: Partial<{entity.name}FormData>;
  isEdit?: boolean;
}}

export default function {entity.name}Form({{ onSubmit, initialData, isEdit = false }}: {entity.name}FormProps) {{
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  const {{
    register,
    handleSubmit,
    formState: {{ errors }},
  }} = useForm<{entity.name}FormData>({{
    resolver: zodResolver({entity.name.lower()}Schema),
    defaultValues: initialData,
  }});

  const handleFormSubmit = async (data: {entity.name}FormData) => {{
    setIsSubmitting(true);
    try {{
      await onSubmit(data);
    }} finally {{
      setIsSubmitting(false);
    }}
  }};

  return (
    <form onSubmit={{handleSubmit(handleFormSubmit)}} className="space-y-4">
      {chr(10).join(form_fields)}

      <button
        type="submit"
        disabled={{isSubmitting}}
        className="w-full py-2 px-4 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {{isSubmitting ? (
          <span className="flex items-center justify-center">
            <Loader2 className="w-5 h-5 mr-2 animate-spin" />
            {{isEdit ? 'Updating...' : 'Creating...'}}
          </span>
        ) : (
          isEdit ? 'Update {entity.name}' : 'Create {entity.name}'
        )}}
      </button>
    </form>
  );
}}
```'''


def generate_fastapi_endpoint(entity: DomainEntity, domain_name: str) -> str:
    """Generate FastAPI CRUD endpoints for an entity"""
    entity_lower = entity.name.lower()
    entity_plural_lower = entity.plural.lower()

    return f'''```python
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.{entity_lower} import {entity.name}
from app.schemas.{entity_lower} import (
    {entity.name}Create,
    {entity.name}Update,
    {entity.name}Response,
    {entity.name}ListResponse,
)

router = APIRouter(prefix="/{entity_plural_lower}", tags=["{entity_plural_lower}"])


@router.get("/", response_model={entity.name}ListResponse)
async def get_{entity_plural_lower}(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get paginated list of {entity_plural_lower}"""
    query = db.query({entity.name})

    if search:
        query = query.filter(
            or_(
                {entity.name}.name.ilike(f"%{{search}}%"),
            )
        )

    total = query.count()
    {entity_plural_lower} = query.offset(skip).limit(limit).all()

    return {entity.name}ListResponse(
        items={entity_plural_lower},
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{{id}}", response_model={entity.name}Response)
async def get_{entity_lower}(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single {entity_lower} by ID"""
    {entity_lower} = db.query({entity.name}).filter({entity.name}.id == id).first()

    if not {entity_lower}:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="{entity.name} not found",
        )

    return {entity_lower}


@router.post("/", response_model={entity.name}Response, status_code=status.HTTP_201_CREATED)
async def create_{entity_lower}(
    {entity_lower}_data: {entity.name}Create,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new {entity_lower}"""
    {entity_lower} = {entity.name}(**{entity_lower}_data.model_dump(), created_by=current_user.id)
    db.add({entity_lower})
    db.commit()
    db.refresh({entity_lower})

    return {entity_lower}


@router.put("/{{id}}", response_model={entity.name}Response)
async def update_{entity_lower}(
    id: UUID,
    {entity_lower}_data: {entity.name}Update,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a {entity_lower}"""
    {entity_lower} = db.query({entity.name}).filter({entity.name}.id == id).first()

    if not {entity_lower}:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="{entity.name} not found",
        )

    update_data = {entity_lower}_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr({entity_lower}, field, value)

    db.commit()
    db.refresh({entity_lower})

    return {entity_lower}


@router.delete("/{{id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_{entity_lower}(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a {entity_lower}"""
    {entity_lower} = db.query({entity.name}).filter({entity.name}.id == id).first()

    if not {entity_lower}:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="{entity.name} not found",
        )

    db.delete({entity_lower})
    db.commit()

    return None
```'''


def generate_sqlalchemy_model(entity: DomainEntity, domain_name: str) -> str:
    """Generate SQLAlchemy model for an entity"""
    entity_lower = entity.name.lower()
    entity_plural_lower = entity.plural.lower()

    columns = []
    for attr_name, attr_type in entity.attributes:
        if attr_type == "string":
            columns.append(f'    {attr_name} = Column(String(255))')
        elif attr_type == "text":
            columns.append(f'    {attr_name} = Column(Text)')
        elif attr_type == "number":
            columns.append(f'    {attr_name} = Column(Integer)')
        elif attr_type == "decimal":
            columns.append(f'    {attr_name} = Column(Float)')
        elif attr_type == "boolean":
            columns.append(f'    {attr_name} = Column(Boolean, default=False)')
        elif attr_type == "date":
            columns.append(f'    {attr_name} = Column(Date)')
        elif attr_type == "datetime":
            columns.append(f'    {attr_name} = Column(DateTime)')
        elif attr_type == "json":
            columns.append(f'    {attr_name} = Column(JSONB, default=dict)')
        elif attr_type.startswith("enum:"):
            columns.append(f'    {attr_name} = Column(String(50))')
        elif attr_type == "uuid":
            columns.append(f'    {attr_name} = Column(UUID(as_uuid=True), ForeignKey("users.id"))')

    # Relationships are handled separately for clarity

    return f'''```python
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid

from app.core.database import Base


class {entity.name}(Base):
    __tablename__ = "{entity_plural_lower}"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

{chr(10).join(columns)}

    # Audit fields
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<{entity.name} {{self.id}}>"
```'''


def generate_pydantic_schema(entity: DomainEntity, domain_name: str) -> str:
    """Generate Pydantic schemas for an entity"""
    entity_lower = entity.name.lower()

    fields = []
    for attr_name, attr_type in entity.attributes:
        if attr_type == "string":
            fields.append(f'    {attr_name}: str')
        elif attr_type == "text":
            fields.append(f'    {attr_name}: Optional[str] = None')
        elif attr_type == "number":
            fields.append(f'    {attr_name}: int')
        elif attr_type == "decimal":
            fields.append(f'    {attr_name}: float')
        elif attr_type == "boolean":
            fields.append(f'    {attr_name}: bool = False')
        elif attr_type == "date":
            fields.append(f'    {attr_name}: date')
        elif attr_type == "datetime":
            fields.append(f'    {attr_name}: datetime')
        elif attr_type == "json":
            fields.append(f'    {attr_name}: Dict[str, Any] = Field(default_factory=dict)')
        elif attr_type.startswith("enum:"):
            fields.append(f'    {attr_name}: str')
        elif attr_type == "uuid":
            fields.append(f'    {attr_name}: UUID')

    optional_fields = []
    for attr_name, attr_type in entity.attributes:
        if attr_type in ["string", "text"]:
            optional_fields.append(f'    {attr_name}: Optional[str] = None')
        elif attr_type == "number":
            optional_fields.append(f'    {attr_name}: Optional[int] = None')
        elif attr_type == "decimal":
            optional_fields.append(f'    {attr_name}: Optional[float] = None')
        elif attr_type == "boolean":
            optional_fields.append(f'    {attr_name}: Optional[bool] = None')
        else:
            optional_fields.append(f'    {attr_name}: Optional[Any] = None')

    return f'''```python
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, date


class {entity.name}Base(BaseModel):
{chr(10).join(fields[:6])}


class {entity.name}Create({entity.name}Base):
    pass


class {entity.name}Update(BaseModel):
{chr(10).join(optional_fields[:6])}


class {entity.name}Response({entity.name}Base):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class {entity.name}ListResponse(BaseModel):
    items: List[{entity.name}Response]
    total: int
    skip: int
    limit: int
```'''


def generate_list_component(entity: DomainEntity, domain_name: str) -> str:
    """Generate React list/table component for an entity"""
    display_attrs = entity.attributes[:5]

    headers = [f'            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{attr[0].replace("_", " ").title()}</th>' for attr in display_attrs]
    cells = [f'              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{item.{attr[0]}}}</td>' for attr in display_attrs]

    return f'''```tsx
import React from 'react';
import {{ useQuery }} from '@tanstack/react-query';
import {{ Loader2, Plus, Search, Edit, Trash2 }} from 'lucide-react';
import {{ api }} from '@/lib/api';

interface {entity.name} {{
  id: string;
{chr(10).join([f"  {attr[0]}: {'string' if attr[1] in ['string', 'text'] else 'number' if attr[1] in ['number', 'decimal'] else 'string'};" for attr in display_attrs])}
}}

interface {entity.name}ListProps {{
  onEdit?: (item: {entity.name}) => void;
  onDelete?: (id: string) => void;
  onCreate?: () => void;
}}

export default function {entity.name}List({{ onEdit, onDelete, onCreate }}: {entity.name}ListProps) {{
  const [search, setSearch] = React.useState('');
  const [page, setPage] = React.useState(1);

  const {{ data, isLoading, error }} = useQuery({{
    queryKey: ['{entity.plural.lower()}', page, search],
    queryFn: () => api.get(`/{entity.plural.lower()}?page=${{page}}&search=${{search}}`),
  }});

  if (isLoading) {{
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }}

  if (error) {{
    return (
      <div className="text-center text-red-600 py-8">
        Failed to load {entity.plural.lower()}
      </div>
    );
  }}

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="p-4 border-b border-gray-200 flex items-center justify-between">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search {entity.plural.lower()}..."
            value={{search}}
            onChange={{(e) => setSearch(e.target.value)}}
            className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
        {{onCreate && (
          <button
            onClick={{onCreate}}
            className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            <Plus className="w-5 h-5 mr-2" />
            Add {entity.name}
          </button>
        )}}
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
{chr(10).join(headers)}
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {{data?.items?.map((item: {entity.name}) => (
              <tr key={{item.id}} className="hover:bg-gray-50">
{chr(10).join(cells)}
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  {{onEdit && (
                    <button onClick={{() => onEdit(item)}} className="text-blue-600 hover:text-blue-900 mr-3">
                      <Edit className="w-5 h-5" />
                    </button>
                  )}}
                  {{onDelete && (
                    <button onClick={{() => onDelete(item.id)}} className="text-red-600 hover:text-red-900">
                      <Trash2 className="w-5 h-5" />
                    </button>
                  )}}
                </td>
              </tr>
            ))}}
          </tbody>
        </table>
      </div>

      <div className="p-4 border-t border-gray-200 flex items-center justify-between">
        <p className="text-sm text-gray-500">
          Showing {{data?.items?.length || 0}} of {{data?.total || 0}} {entity.plural.lower()}
        </p>
        <div className="flex space-x-2">
          <button
            onClick={{() => setPage(p => Math.max(1, p - 1))}}
            disabled={{page === 1}}
            className="px-4 py-2 border border-gray-300 rounded-lg disabled:opacity-50"
          >
            Previous
          </button>
          <button
            onClick={{() => setPage(p => p + 1)}}
            disabled={{!data?.hasMore}}
            className="px-4 py-2 border border-gray-300 rounded-lg disabled:opacity-50"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}}
```'''


# ============================================================================
# SAMPLE GENERATION
# ============================================================================

def generate_domain_samples(domain_key: str, domain_config: dict) -> List[Dict]:
    """Generate all training samples for a domain"""
    samples = []
    domain_name = domain_config["name"]

    for entity in domain_config["entities"]:
        # React Form Component
        samples.append({
            "messages": [
                {"role": "system", "content": f"You are an expert full-stack developer building a {domain_name}."},
                {"role": "user", "content": f"Create a React form component for {entity.name} with TypeScript and Tailwind CSS"},
                {"role": "assistant", "content": generate_react_component(entity, domain_name)}
            ]
        })

        # React List Component
        samples.append({
            "messages": [
                {"role": "system", "content": f"You are an expert full-stack developer building a {domain_name}."},
                {"role": "user", "content": f"Create a React table/list component for displaying {entity.plural} with search, pagination, and actions"},
                {"role": "assistant", "content": generate_list_component(entity, domain_name)}
            ]
        })

        # FastAPI Endpoints
        samples.append({
            "messages": [
                {"role": "system", "content": f"You are an expert Python backend developer building a {domain_name}."},
                {"role": "user", "content": f"Create FastAPI CRUD endpoints for {entity.name} management"},
                {"role": "assistant", "content": generate_fastapi_endpoint(entity, domain_name)}
            ]
        })

        # SQLAlchemy Model
        samples.append({
            "messages": [
                {"role": "system", "content": f"You are an expert Python backend developer building a {domain_name}."},
                {"role": "user", "content": f"Create a SQLAlchemy model for {entity.name} with appropriate fields and relationships"},
                {"role": "assistant", "content": generate_sqlalchemy_model(entity, domain_name)}
            ]
        })

        # Pydantic Schemas
        samples.append({
            "messages": [
                {"role": "system", "content": f"You are an expert Python backend developer building a {domain_name}."},
                {"role": "user", "content": f"Create Pydantic schemas for {entity.name} (Create, Update, Response)"},
                {"role": "assistant", "content": generate_pydantic_schema(entity, domain_name)}
            ]
        })

    # Add domain-specific feature samples
    for feature in domain_config.get("features", []):
        samples.append({
            "messages": [
                {"role": "system", "content": f"You are an expert full-stack developer building a {domain_name}."},
                {"role": "user", "content": f"Implement {feature} feature for the {domain_name}"},
                {"role": "assistant", "content": f"[FEATURE_IMPLEMENTATION:{feature}]"}
            ]
        })

    return samples


def generate_all_domain_samples() -> List[Dict]:
    """Generate training samples for all domains"""
    all_samples = []

    for domain_key, domain_config in DOMAINS.items():
        print(f"Generating samples for {domain_config['name']}...")
        samples = generate_domain_samples(domain_key, domain_config)
        all_samples.extend(samples)
        print(f"  Generated {len(samples)} samples")

    return all_samples


def save_domain_samples(output_dir: str = "./data/domains"):
    """Save domain samples to file"""
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    samples = generate_all_domain_samples()

    # Filter out placeholder samples
    real_samples = [s for s in samples if not s["messages"][2]["content"].startswith("[")]

    output_file = Path(output_dir) / "all_domains.jsonl"
    with open(output_file, "w", encoding="utf-8") as f:
        for sample in real_samples:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")

    print(f"\n{'='*60}")
    print(f"Total domains: {len(DOMAINS)}")
    print(f"Total samples generated: {len(samples)}")
    print(f"Real samples (with code): {len(real_samples)}")
    print(f"Saved to: {output_file}")

    # Print domain breakdown
    print(f"\n{'='*60}")
    print("Domain breakdown:")
    for domain_key, domain_config in DOMAINS.items():
        entity_count = len(domain_config["entities"])
        # 5 samples per entity (form, list, api, model, schema)
        sample_count = entity_count * 5
        print(f"  {domain_config['name']}: {entity_count} entities, {sample_count} samples")

    return real_samples


if __name__ == "__main__":
    save_domain_samples()
