"""
Comprehensive Domain-Agnostic Training Data Generator
Covers 50+ domains with extensive entity coverage
"""
import json
import random
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class Entity:
    """Represents an entity in a domain"""
    name: str
    plural: str
    attributes: List[Tuple[str, str]]  # [(name, type), ...]


# ============================================================================
# 50+ DOMAINS WITH COMPREHENSIVE ENTITY COVERAGE
# ============================================================================

DOMAINS = {
    # ==================== HEALTHCARE & MEDICAL ====================
    "hospital_management": {
        "name": "Hospital Management System",
        "entities": [
            Entity("Patient", "Patients", [
                ("name", "string"), ("email", "string"), ("phone", "string"),
                ("dateOfBirth", "date"), ("gender", "enum:male,female,other"),
                ("bloodGroup", "string"), ("address", "text"), ("emergencyContact", "string"),
                ("insuranceProvider", "string"), ("insuranceNumber", "string")
            ]),
            Entity("Doctor", "Doctors", [
                ("name", "string"), ("email", "string"), ("specialization", "string"),
                ("qualification", "string"), ("licenseNumber", "string"), ("experience", "number"),
                ("consultationFee", "decimal"), ("rating", "decimal"), ("availability", "json")
            ]),
            Entity("Appointment", "Appointments", [
                ("scheduledAt", "datetime"), ("duration", "number"), ("status", "enum:scheduled,confirmed,completed,cancelled"),
                ("type", "enum:consultation,followup,emergency"), ("symptoms", "text"), ("notes", "text")
            ]),
            Entity("MedicalRecord", "MedicalRecords", [
                ("diagnosis", "text"), ("treatment", "text"), ("medications", "json"),
                ("labResults", "json"), ("vitals", "json"), ("attachments", "json")
            ]),
            Entity("Prescription", "Prescriptions", [
                ("medications", "json"), ("dosage", "text"), ("instructions", "text"),
                ("validUntil", "date"), ("refillsAllowed", "number")
            ]),
            Entity("Ward", "Wards", [
                ("name", "string"), ("type", "enum:general,icu,emergency,pediatric,maternity"),
                ("capacity", "number"), ("occupiedBeds", "number"), ("floor", "number")
            ]),
            Entity("LabTest", "LabTests", [
                ("name", "string"), ("type", "string"), ("price", "decimal"),
                ("turnaroundTime", "number"), ("instructions", "text")
            ]),
        ]
    },

    "pharmacy": {
        "name": "Pharmacy Management System",
        "entities": [
            Entity("Medicine", "Medicines", [
                ("name", "string"), ("genericName", "string"), ("manufacturer", "string"),
                ("category", "string"), ("dosageForm", "enum:tablet,capsule,syrup,injection,cream"),
                ("strength", "string"), ("price", "decimal"), ("stock", "number"),
                ("expiryDate", "date"), ("requiresPrescription", "boolean")
            ]),
            Entity("PrescriptionOrder", "PrescriptionOrders", [
                ("prescriptionImage", "string"), ("status", "enum:pending,verified,dispensed,rejected"),
                ("totalAmount", "decimal"), ("verifiedBy", "uuid"), ("notes", "text")
            ]),
            Entity("Supplier", "Suppliers", [
                ("name", "string"), ("email", "string"), ("phone", "string"),
                ("address", "text"), ("gstNumber", "string"), ("paymentTerms", "string")
            ]),
            Entity("PurchaseOrder", "PurchaseOrders", [
                ("orderNumber", "string"), ("status", "enum:draft,ordered,received,cancelled"),
                ("totalAmount", "decimal"), ("expectedDelivery", "date")
            ]),
            Entity("Sale", "Sales", [
                ("invoiceNumber", "string"), ("items", "json"), ("subtotal", "decimal"),
                ("discount", "decimal"), ("tax", "decimal"), ("total", "decimal"),
                ("paymentMethod", "enum:cash,card,upi")
            ]),
        ]
    },

    "dental_clinic": {
        "name": "Dental Clinic Management",
        "entities": [
            Entity("DentalPatient", "DentalPatients", [
                ("name", "string"), ("email", "string"), ("phone", "string"),
                ("dateOfBirth", "date"), ("dentalHistory", "json"), ("allergies", "text")
            ]),
            Entity("Dentist", "Dentists", [
                ("name", "string"), ("specialization", "enum:general,orthodontics,periodontics,endodontics"),
                ("licenseNumber", "string"), ("experience", "number")
            ]),
            Entity("DentalTreatment", "DentalTreatments", [
                ("name", "string"), ("description", "text"), ("price", "decimal"),
                ("duration", "number"), ("category", "string")
            ]),
            Entity("DentalAppointment", "DentalAppointments", [
                ("scheduledAt", "datetime"), ("treatment", "string"), ("status", "enum:scheduled,completed,cancelled"),
                ("toothNumber", "string"), ("notes", "text")
            ]),
        ]
    },

    # ==================== EDUCATION ====================
    "school_management": {
        "name": "School Management System",
        "entities": [
            Entity("Student", "Students", [
                ("firstName", "string"), ("lastName", "string"), ("rollNumber", "string"),
                ("dateOfBirth", "date"), ("gender", "enum:male,female,other"), ("grade", "string"),
                ("section", "string"), ("admissionDate", "date"), ("parentName", "string"),
                ("parentPhone", "string"), ("address", "text")
            ]),
            Entity("Teacher", "Teachers", [
                ("name", "string"), ("email", "string"), ("phone", "string"),
                ("subjects", "json"), ("qualification", "string"), ("experience", "number"),
                ("joiningDate", "date"), ("salary", "decimal")
            ]),
            Entity("Class", "Classes", [
                ("name", "string"), ("grade", "string"), ("section", "string"),
                ("capacity", "number"), ("classTeacher", "uuid"), ("room", "string")
            ]),
            Entity("Subject", "Subjects", [
                ("name", "string"), ("code", "string"), ("credits", "number"),
                ("type", "enum:core,elective"), ("syllabus", "text")
            ]),
            Entity("Exam", "Exams", [
                ("name", "string"), ("type", "enum:unit,midterm,final,practical"),
                ("subject", "uuid"), ("date", "date"), ("duration", "number"),
                ("totalMarks", "number"), ("passingMarks", "number")
            ]),
            Entity("Result", "Results", [
                ("marksObtained", "number"), ("grade", "string"), ("remarks", "text"),
                ("rank", "number")
            ]),
            Entity("Attendance", "Attendances", [
                ("date", "date"), ("status", "enum:present,absent,late,excused"),
                ("remarks", "text")
            ]),
            Entity("Fee", "Fees", [
                ("type", "enum:tuition,transport,library,laboratory,sports"),
                ("amount", "decimal"), ("dueDate", "date"), ("paidDate", "date"),
                ("status", "enum:pending,paid,overdue"), ("receiptNumber", "string")
            ]),
        ]
    },

    "university": {
        "name": "University Management System",
        "entities": [
            Entity("UniversityStudent", "UniversityStudents", [
                ("name", "string"), ("email", "string"), ("enrollmentNumber", "string"),
                ("program", "string"), ("department", "string"), ("semester", "number"),
                ("cgpa", "decimal"), ("status", "enum:active,graduated,dropped")
            ]),
            Entity("Professor", "Professors", [
                ("name", "string"), ("email", "string"), ("department", "string"),
                ("designation", "enum:assistant,associate,professor,hod"),
                ("researchAreas", "json"), ("publications", "number")
            ]),
            Entity("Course", "Courses", [
                ("code", "string"), ("name", "string"), ("credits", "number"),
                ("department", "string"), ("semester", "number"), ("syllabus", "text"),
                ("prerequisites", "json")
            ]),
            Entity("Department", "Departments", [
                ("name", "string"), ("code", "string"), ("head", "uuid"),
                ("faculty", "number"), ("students", "number")
            ]),
            Entity("ResearchProject", "ResearchProjects", [
                ("title", "string"), ("abstract", "text"), ("status", "enum:proposed,ongoing,completed"),
                ("funding", "decimal"), ("duration", "number")
            ]),
        ]
    },

    "online_learning": {
        "name": "Online Learning Platform",
        "entities": [
            Entity("Learner", "Learners", [
                ("name", "string"), ("email", "string"), ("avatar", "string"),
                ("bio", "text"), ("interests", "json"), ("completedCourses", "number")
            ]),
            Entity("OnlineCourse", "OnlineCourses", [
                ("title", "string"), ("description", "text"), ("thumbnail", "string"),
                ("level", "enum:beginner,intermediate,advanced"), ("duration", "number"),
                ("price", "decimal"), ("rating", "decimal"), ("enrollments", "number"),
                ("language", "string"), ("isPublished", "boolean")
            ]),
            Entity("Module", "Modules", [
                ("title", "string"), ("description", "text"), ("order", "number"),
                ("duration", "number")
            ]),
            Entity("Lesson", "Lessons", [
                ("title", "string"), ("type", "enum:video,article,quiz,assignment"),
                ("content", "text"), ("videoUrl", "string"), ("duration", "number"),
                ("order", "number")
            ]),
            Entity("Quiz", "Quizzes", [
                ("title", "string"), ("questions", "json"), ("passingScore", "number"),
                ("timeLimit", "number"), ("attempts", "number")
            ]),
            Entity("Certificate", "Certificates", [
                ("certificateNumber", "string"), ("issuedAt", "datetime"),
                ("grade", "string"), ("downloadUrl", "string")
            ]),
            Entity("Review", "Reviews", [
                ("rating", "number"), ("comment", "text"), ("isVerified", "boolean")
            ]),
        ]
    },

    # ==================== E-COMMERCE & RETAIL ====================
    "ecommerce": {
        "name": "E-Commerce Platform",
        "entities": [
            Entity("Product", "Products", [
                ("name", "string"), ("slug", "string"), ("description", "text"),
                ("price", "decimal"), ("comparePrice", "decimal"), ("sku", "string"),
                ("barcode", "string"), ("stock", "number"), ("images", "json"),
                ("category", "string"), ("brand", "string"), ("tags", "json"),
                ("isActive", "boolean"), ("isFeatured", "boolean")
            ]),
            Entity("Category", "Categories", [
                ("name", "string"), ("slug", "string"), ("description", "text"),
                ("image", "string"), ("parent", "uuid"), ("order", "number")
            ]),
            Entity("Order", "Orders", [
                ("orderNumber", "string"), ("status", "enum:pending,confirmed,processing,shipped,delivered,cancelled"),
                ("items", "json"), ("subtotal", "decimal"), ("shipping", "decimal"),
                ("tax", "decimal"), ("discount", "decimal"), ("total", "decimal"),
                ("shippingAddress", "json"), ("billingAddress", "json"),
                ("paymentMethod", "string"), ("paymentStatus", "enum:pending,paid,failed,refunded")
            ]),
            Entity("Cart", "Carts", [
                ("items", "json"), ("subtotal", "decimal"), ("itemCount", "number")
            ]),
            Entity("Wishlist", "Wishlists", [
                ("products", "json")
            ]),
            Entity("Coupon", "Coupons", [
                ("code", "string"), ("type", "enum:percentage,fixed"),
                ("value", "decimal"), ("minPurchase", "decimal"), ("maxDiscount", "decimal"),
                ("usageLimit", "number"), ("usedCount", "number"),
                ("validFrom", "date"), ("validUntil", "date"), ("isActive", "boolean")
            ]),
            Entity("ProductReview", "ProductReviews", [
                ("rating", "number"), ("title", "string"), ("comment", "text"),
                ("images", "json"), ("isVerified", "boolean"), ("helpful", "number")
            ]),
            Entity("Shipment", "Shipments", [
                ("trackingNumber", "string"), ("carrier", "string"),
                ("status", "enum:processing,shipped,intransit,outfordelivery,delivered"),
                ("estimatedDelivery", "date"), ("actualDelivery", "date")
            ]),
        ]
    },

    "marketplace": {
        "name": "Multi-Vendor Marketplace",
        "entities": [
            Entity("Vendor", "Vendors", [
                ("storeName", "string"), ("slug", "string"), ("description", "text"),
                ("logo", "string"), ("banner", "string"), ("rating", "decimal"),
                ("totalSales", "number"), ("commission", "decimal"),
                ("status", "enum:pending,approved,suspended"), ("bankDetails", "json")
            ]),
            Entity("VendorProduct", "VendorProducts", [
                ("name", "string"), ("description", "text"), ("price", "decimal"),
                ("stock", "number"), ("images", "json"), ("status", "enum:pending,approved,rejected")
            ]),
            Entity("Payout", "Payouts", [
                ("amount", "decimal"), ("status", "enum:pending,processing,completed,failed"),
                ("method", "string"), ("reference", "string")
            ]),
            Entity("Dispute", "Disputes", [
                ("reason", "string"), ("description", "text"),
                ("status", "enum:open,investigating,resolved,closed"),
                ("resolution", "text")
            ]),
        ]
    },

    "pos_retail": {
        "name": "POS & Retail Management",
        "entities": [
            Entity("RetailProduct", "RetailProducts", [
                ("name", "string"), ("sku", "string"), ("barcode", "string"),
                ("price", "decimal"), ("cost", "decimal"), ("stock", "number"),
                ("reorderLevel", "number"), ("category", "string"), ("unit", "string")
            ]),
            Entity("RetailSale", "RetailSales", [
                ("invoiceNumber", "string"), ("items", "json"), ("subtotal", "decimal"),
                ("discount", "decimal"), ("tax", "decimal"), ("total", "decimal"),
                ("paymentMethod", "enum:cash,card,upi,credit"), ("cashier", "uuid")
            ]),
            Entity("Customer", "Customers", [
                ("name", "string"), ("phone", "string"), ("email", "string"),
                ("loyaltyPoints", "number"), ("totalPurchases", "decimal")
            ]),
            Entity("CashDrawer", "CashDrawers", [
                ("openingBalance", "decimal"), ("closingBalance", "decimal"),
                ("cashSales", "decimal"), ("cardSales", "decimal"),
                ("status", "enum:open,closed")
            ]),
        ]
    },

    # ==================== FOOD & RESTAURANT ====================
    "restaurant": {
        "name": "Restaurant Management System",
        "entities": [
            Entity("Restaurant", "Restaurants", [
                ("name", "string"), ("description", "text"), ("cuisine", "json"),
                ("address", "text"), ("phone", "string"), ("email", "string"),
                ("openingHours", "json"), ("rating", "decimal"), ("priceRange", "string"),
                ("images", "json"), ("isOpen", "boolean")
            ]),
            Entity("MenuItem", "MenuItems", [
                ("name", "string"), ("description", "text"), ("price", "decimal"),
                ("category", "string"), ("image", "string"), ("isVeg", "boolean"),
                ("spiceLevel", "enum:mild,medium,hot,extra_hot"),
                ("allergens", "json"), ("calories", "number"), ("isAvailable", "boolean")
            ]),
            Entity("Table", "Tables", [
                ("number", "number"), ("capacity", "number"), ("location", "string"),
                ("status", "enum:available,occupied,reserved,maintenance")
            ]),
            Entity("Reservation", "Reservations", [
                ("date", "date"), ("time", "string"), ("guests", "number"),
                ("status", "enum:pending,confirmed,seated,completed,cancelled,noshow"),
                ("specialRequests", "text")
            ]),
            Entity("FoodOrder", "FoodOrders", [
                ("orderNumber", "string"), ("type", "enum:dinein,takeaway,delivery"),
                ("items", "json"), ("status", "enum:placed,preparing,ready,served,completed"),
                ("subtotal", "decimal"), ("tax", "decimal"), ("total", "decimal"),
                ("paymentStatus", "enum:pending,paid"), ("specialInstructions", "text")
            ]),
            Entity("KitchenOrder", "KitchenOrders", [
                ("items", "json"), ("priority", "enum:normal,rush"),
                ("status", "enum:pending,cooking,ready"), ("prepTime", "number")
            ]),
        ]
    },

    "food_delivery": {
        "name": "Food Delivery Platform",
        "entities": [
            Entity("DeliveryRestaurant", "DeliveryRestaurants", [
                ("name", "string"), ("cuisine", "json"), ("rating", "decimal"),
                ("deliveryTime", "string"), ("minOrder", "decimal"),
                ("deliveryFee", "decimal"), ("isActive", "boolean")
            ]),
            Entity("DeliveryOrder", "DeliveryOrders", [
                ("orderNumber", "string"), ("items", "json"), ("total", "decimal"),
                ("status", "enum:placed,confirmed,preparing,pickedup,delivered,cancelled"),
                ("deliveryAddress", "text"), ("deliveryInstructions", "text"),
                ("estimatedDelivery", "datetime")
            ]),
            Entity("DeliveryPartner", "DeliveryPartners", [
                ("name", "string"), ("phone", "string"), ("vehicleType", "enum:bike,scooter,car"),
                ("vehicleNumber", "string"), ("currentLocation", "json"),
                ("status", "enum:online,offline,busy"), ("rating", "decimal"),
                ("totalDeliveries", "number")
            ]),
            Entity("DeliveryTracking", "DeliveryTrackings", [
                ("status", "string"), ("location", "json"), ("timestamp", "datetime"),
                ("message", "string")
            ]),
        ]
    },

    "cloud_kitchen": {
        "name": "Cloud Kitchen Management",
        "entities": [
            Entity("Kitchen", "Kitchens", [
                ("name", "string"), ("brands", "json"), ("capacity", "number"),
                ("operatingHours", "json"), ("status", "enum:active,inactive")
            ]),
            Entity("KitchenBrand", "KitchenBrands", [
                ("name", "string"), ("cuisine", "string"), ("logo", "string"),
                ("menu", "json"), ("isActive", "boolean")
            ]),
            Entity("KitchenOrder", "KitchenOrders", [
                ("brand", "uuid"), ("items", "json"), ("platform", "string"),
                ("status", "enum:received,preparing,ready,dispatched"),
                ("prepTime", "number")
            ]),
            Entity("Ingredient", "Ingredients", [
                ("name", "string"), ("unit", "string"), ("stock", "number"),
                ("reorderLevel", "number"), ("cost", "decimal")
            ]),
        ]
    },

    # ==================== REAL ESTATE & PROPERTY ====================
    "real_estate": {
        "name": "Real Estate Platform",
        "entities": [
            Entity("Property", "Properties", [
                ("title", "string"), ("description", "text"), ("type", "enum:apartment,house,villa,plot,commercial"),
                ("purpose", "enum:sale,rent"), ("price", "decimal"), ("area", "decimal"),
                ("bedrooms", "number"), ("bathrooms", "number"), ("parking", "number"),
                ("address", "text"), ("city", "string"), ("state", "string"),
                ("zipcode", "string"), ("coordinates", "json"), ("amenities", "json"),
                ("images", "json"), ("virtualTour", "string"), ("status", "enum:available,sold,rented")
            ]),
            Entity("Agent", "Agents", [
                ("name", "string"), ("email", "string"), ("phone", "string"),
                ("photo", "string"), ("license", "string"), ("experience", "number"),
                ("specialization", "json"), ("rating", "decimal"), ("listings", "number")
            ]),
            Entity("PropertyInquiry", "PropertyInquiries", [
                ("name", "string"), ("email", "string"), ("phone", "string"),
                ("message", "text"), ("preferredTime", "string"),
                ("status", "enum:new,contacted,scheduled,closed")
            ]),
            Entity("PropertyViewing", "PropertyViewings", [
                ("scheduledAt", "datetime"), ("status", "enum:scheduled,completed,cancelled,noshow"),
                ("feedback", "text"), ("interested", "boolean")
            ]),
            Entity("RentalAgreement", "RentalAgreements", [
                ("startDate", "date"), ("endDate", "date"), ("rent", "decimal"),
                ("deposit", "decimal"), ("terms", "text"), ("status", "enum:active,expired,terminated")
            ]),
        ]
    },

    "property_management": {
        "name": "Property Management System",
        "entities": [
            Entity("Building", "Buildings", [
                ("name", "string"), ("address", "text"), ("units", "number"),
                ("floors", "number"), ("amenities", "json"), ("manager", "uuid")
            ]),
            Entity("Unit", "Units", [
                ("number", "string"), ("type", "enum:studio,1bhk,2bhk,3bhk,penthouse"),
                ("area", "decimal"), ("rent", "decimal"), ("status", "enum:vacant,occupied,maintenance")
            ]),
            Entity("Tenant", "Tenants", [
                ("name", "string"), ("email", "string"), ("phone", "string"),
                ("leaseStart", "date"), ("leaseEnd", "date"), ("rent", "decimal"),
                ("deposit", "decimal"), ("status", "enum:active,notice,moved_out")
            ]),
            Entity("MaintenanceRequest", "MaintenanceRequests", [
                ("title", "string"), ("description", "text"), ("category", "string"),
                ("priority", "enum:low,medium,high,emergency"),
                ("status", "enum:open,assigned,inprogress,completed"),
                ("assignedTo", "uuid"), ("cost", "decimal")
            ]),
            Entity("RentPayment", "RentPayments", [
                ("amount", "decimal"), ("dueDate", "date"), ("paidDate", "date"),
                ("status", "enum:pending,paid,late,waived"), ("lateFee", "decimal")
            ]),
        ]
    },

    # ==================== FINANCE & BANKING ====================
    "banking": {
        "name": "Banking Application",
        "entities": [
            Entity("BankAccount", "BankAccounts", [
                ("accountNumber", "string"), ("type", "enum:savings,current,fixed,recurring"),
                ("balance", "decimal"), ("currency", "string"), ("status", "enum:active,frozen,closed"),
                ("interestRate", "decimal"), ("branch", "string")
            ]),
            Entity("Transaction", "Transactions", [
                ("transactionId", "string"), ("type", "enum:credit,debit,transfer"),
                ("amount", "decimal"), ("description", "text"), ("category", "string"),
                ("status", "enum:pending,completed,failed,reversed"),
                ("referenceNumber", "string")
            ]),
            Entity("BankTransfer", "BankTransfers", [
                ("fromAccount", "string"), ("toAccount", "string"), ("amount", "decimal"),
                ("type", "enum:imps,neft,rtgs,upi"), ("status", "enum:pending,completed,failed"),
                ("remarks", "text")
            ]),
            Entity("Loan", "Loans", [
                ("loanNumber", "string"), ("type", "enum:personal,home,car,education,business"),
                ("principal", "decimal"), ("interestRate", "decimal"), ("tenure", "number"),
                ("emi", "decimal"), ("outstanding", "decimal"),
                ("status", "enum:applied,approved,disbursed,closed")
            ]),
            Entity("Card", "Cards", [
                ("cardNumber", "string"), ("type", "enum:debit,credit"),
                ("variant", "string"), ("limit", "decimal"), ("used", "decimal"),
                ("expiryDate", "date"), ("status", "enum:active,blocked,expired")
            ]),
            Entity("Beneficiary", "Beneficiaries", [
                ("name", "string"), ("accountNumber", "string"), ("bankName", "string"),
                ("ifscCode", "string"), ("nickname", "string")
            ]),
        ]
    },

    "investment": {
        "name": "Investment Platform",
        "entities": [
            Entity("Portfolio", "Portfolios", [
                ("name", "string"), ("value", "decimal"), ("invested", "decimal"),
                ("returns", "decimal"), ("returnPercentage", "decimal")
            ]),
            Entity("Stock", "Stocks", [
                ("symbol", "string"), ("name", "string"), ("exchange", "string"),
                ("price", "decimal"), ("change", "decimal"), ("changePercent", "decimal"),
                ("volume", "number"), ("marketCap", "decimal")
            ]),
            Entity("StockHolding", "StockHoldings", [
                ("symbol", "string"), ("quantity", "number"), ("avgPrice", "decimal"),
                ("currentPrice", "decimal"), ("invested", "decimal"), ("currentValue", "decimal")
            ]),
            Entity("MutualFund", "MutualFunds", [
                ("name", "string"), ("category", "string"), ("nav", "decimal"),
                ("aum", "decimal"), ("expense", "decimal"), ("returns1Y", "decimal"),
                ("returns3Y", "decimal"), ("returns5Y", "decimal")
            ]),
            Entity("SIP", "SIPs", [
                ("fundName", "string"), ("amount", "decimal"), ("frequency", "enum:monthly,weekly,quarterly"),
                ("startDate", "date"), ("status", "enum:active,paused,cancelled")
            ]),
            Entity("TradeOrder", "TradeOrders", [
                ("symbol", "string"), ("type", "enum:buy,sell"), ("orderType", "enum:market,limit,stoploss"),
                ("quantity", "number"), ("price", "decimal"), ("status", "enum:pending,executed,cancelled")
            ]),
        ]
    },

    "insurance": {
        "name": "Insurance Management System",
        "entities": [
            Entity("Policy", "Policies", [
                ("policyNumber", "string"), ("type", "enum:life,health,motor,home,travel"),
                ("premium", "decimal"), ("sumInsured", "decimal"),
                ("startDate", "date"), ("endDate", "date"),
                ("status", "enum:active,lapsed,cancelled,claimed")
            ]),
            Entity("Claim", "Claims", [
                ("claimNumber", "string"), ("type", "string"), ("amount", "decimal"),
                ("description", "text"), ("documents", "json"),
                ("status", "enum:submitted,processing,approved,rejected,settled")
            ]),
            Entity("Premium", "Premiums", [
                ("amount", "decimal"), ("dueDate", "date"), ("paidDate", "date"),
                ("status", "enum:pending,paid,overdue"), ("paymentMethod", "string")
            ]),
            Entity("Nominee", "Nominees", [
                ("name", "string"), ("relationship", "string"), ("percentage", "decimal"),
                ("dateOfBirth", "date"), ("address", "text")
            ]),
        ]
    },

    "accounting": {
        "name": "Accounting Software",
        "entities": [
            Entity("Account", "Accounts", [
                ("code", "string"), ("name", "string"), ("type", "enum:asset,liability,equity,revenue,expense"),
                ("balance", "decimal"), ("parent", "uuid")
            ]),
            Entity("JournalEntry", "JournalEntries", [
                ("entryNumber", "string"), ("date", "date"), ("description", "text"),
                ("debitTotal", "decimal"), ("creditTotal", "decimal"),
                ("status", "enum:draft,posted,voided")
            ]),
            Entity("Invoice", "Invoices", [
                ("invoiceNumber", "string"), ("type", "enum:sales,purchase"),
                ("date", "date"), ("dueDate", "date"), ("items", "json"),
                ("subtotal", "decimal"), ("tax", "decimal"), ("total", "decimal"),
                ("status", "enum:draft,sent,paid,overdue,cancelled")
            ]),
            Entity("Expense", "Expenses", [
                ("date", "date"), ("category", "string"), ("amount", "decimal"),
                ("description", "text"), ("receipt", "string"), ("status", "enum:pending,approved,rejected")
            ]),
            Entity("TaxReturn", "TaxReturns", [
                ("year", "string"), ("type", "string"), ("income", "decimal"),
                ("deductions", "decimal"), ("taxPayable", "decimal"),
                ("status", "enum:draft,filed,processed")
            ]),
        ]
    },

    # ==================== HR & RECRUITMENT ====================
    "hrms": {
        "name": "HR Management System",
        "entities": [
            Entity("Employee", "Employees", [
                ("employeeId", "string"), ("name", "string"), ("email", "string"),
                ("phone", "string"), ("department", "string"), ("designation", "string"),
                ("manager", "uuid"), ("joiningDate", "date"), ("salary", "decimal"),
                ("status", "enum:active,probation,notice,resigned,terminated")
            ]),
            Entity("Department", "Departments", [
                ("name", "string"), ("code", "string"), ("head", "uuid"),
                ("budget", "decimal"), ("headcount", "number")
            ]),
            Entity("LeaveRequest", "LeaveRequests", [
                ("type", "enum:casual,sick,earned,maternity,paternity,unpaid"),
                ("startDate", "date"), ("endDate", "date"), ("days", "number"),
                ("reason", "text"), ("status", "enum:pending,approved,rejected")
            ]),
            Entity("Attendance", "Attendances", [
                ("date", "date"), ("checkIn", "datetime"), ("checkOut", "datetime"),
                ("status", "enum:present,absent,halfday,wfh,holiday"),
                ("overtime", "number")
            ]),
            Entity("Payroll", "Payrolls", [
                ("month", "string"), ("basic", "decimal"), ("hra", "decimal"),
                ("allowances", "decimal"), ("deductions", "decimal"),
                ("tax", "decimal"), ("netPay", "decimal"), ("status", "enum:draft,processed,paid")
            ]),
            Entity("PerformanceReview", "PerformanceReviews", [
                ("period", "string"), ("rating", "number"), ("goals", "json"),
                ("achievements", "text"), ("feedback", "text"),
                ("status", "enum:pending,selfReview,managerReview,completed")
            ]),
            Entity("Training", "Trainings", [
                ("title", "string"), ("description", "text"), ("type", "string"),
                ("date", "date"), ("duration", "number"), ("trainer", "string"),
                ("status", "enum:scheduled,completed,cancelled")
            ]),
        ]
    },

    "recruitment": {
        "name": "Recruitment & ATS System",
        "entities": [
            Entity("JobPosting", "JobPostings", [
                ("title", "string"), ("description", "text"), ("department", "string"),
                ("location", "string"), ("type", "enum:fulltime,parttime,contract,internship"),
                ("experience", "string"), ("salary", "json"), ("skills", "json"),
                ("deadline", "date"), ("status", "enum:draft,active,closed,filled")
            ]),
            Entity("Candidate", "Candidates", [
                ("name", "string"), ("email", "string"), ("phone", "string"),
                ("resumeUrl", "string"), ("linkedIn", "string"),
                ("experience", "number"), ("skills", "json"), ("source", "string")
            ]),
            Entity("Application", "Applications", [
                ("status", "enum:applied,screening,interview,offered,hired,rejected"),
                ("appliedAt", "datetime"), ("resumeUrl", "string"),
                ("coverLetter", "text"), ("notes", "text")
            ]),
            Entity("Interview", "Interviews", [
                ("scheduledAt", "datetime"), ("type", "enum:phone,video,onsite,technical"),
                ("round", "number"), ("interviewer", "uuid"),
                ("status", "enum:scheduled,completed,cancelled"),
                ("feedback", "text"), ("rating", "number")
            ]),
            Entity("Offer", "Offers", [
                ("position", "string"), ("salary", "decimal"), ("joiningDate", "date"),
                ("benefits", "json"), ("status", "enum:draft,sent,accepted,rejected,withdrawn"),
                ("expiryDate", "date")
            ]),
        ]
    },

    # ==================== LOGISTICS & SUPPLY CHAIN ====================
    "logistics": {
        "name": "Logistics Management System",
        "entities": [
            Entity("Shipment", "Shipments", [
                ("trackingNumber", "string"), ("origin", "json"), ("destination", "json"),
                ("weight", "decimal"), ("dimensions", "json"),
                ("type", "enum:standard,express,overnight,freight"),
                ("status", "enum:booked,picked,intransit,outfordelivery,delivered"),
                ("estimatedDelivery", "date"), ("actualDelivery", "date"), ("cost", "decimal")
            ]),
            Entity("Warehouse", "Warehouses", [
                ("name", "string"), ("address", "text"), ("capacity", "number"),
                ("occupancy", "number"), ("type", "enum:distribution,fulfillment,cold_storage"),
                ("coordinates", "json")
            ]),
            Entity("Vehicle", "Vehicles", [
                ("vehicleNumber", "string"), ("type", "enum:bike,van,truck,trailer"),
                ("capacity", "decimal"), ("currentLocation", "json"),
                ("status", "enum:available,intransit,maintenance"),
                ("driver", "uuid")
            ]),
            Entity("Driver", "Drivers", [
                ("name", "string"), ("phone", "string"), ("license", "string"),
                ("currentLocation", "json"), ("status", "enum:available,onduty,offline"),
                ("rating", "decimal"), ("deliveries", "number")
            ]),
            Entity("Route", "Routes", [
                ("name", "string"), ("origin", "string"), ("destination", "string"),
                ("distance", "decimal"), ("estimatedTime", "number"),
                ("waypoints", "json"), ("isActive", "boolean")
            ]),
            Entity("DeliveryProof", "DeliveryProofs", [
                ("signature", "string"), ("photo", "string"),
                ("receiverName", "string"), ("timestamp", "datetime"),
                ("location", "json"), ("notes", "text")
            ]),
        ]
    },

    "inventory": {
        "name": "Inventory Management System",
        "entities": [
            Entity("InventoryItem", "InventoryItems", [
                ("name", "string"), ("sku", "string"), ("barcode", "string"),
                ("category", "string"), ("unit", "string"),
                ("costPrice", "decimal"), ("sellingPrice", "decimal"),
                ("stock", "number"), ("reorderLevel", "number"), ("maxStock", "number")
            ]),
            Entity("StockMovement", "StockMovements", [
                ("type", "enum:purchase,sale,adjustment,transfer,return"),
                ("quantity", "number"), ("unitCost", "decimal"),
                ("reference", "string"), ("notes", "text")
            ]),
            Entity("PurchaseOrder", "PurchaseOrders", [
                ("poNumber", "string"), ("supplier", "uuid"), ("items", "json"),
                ("total", "decimal"), ("status", "enum:draft,ordered,partial,received,cancelled"),
                ("expectedDate", "date")
            ]),
            Entity("StockTransfer", "StockTransfers", [
                ("fromWarehouse", "uuid"), ("toWarehouse", "uuid"),
                ("items", "json"), ("status", "enum:pending,intransit,received"),
                ("shippedAt", "datetime"), ("receivedAt", "datetime")
            ]),
            Entity("StockCount", "StockCounts", [
                ("date", "date"), ("items", "json"), ("status", "enum:pending,inprogress,completed"),
                ("discrepancies", "json")
            ]),
        ]
    },

    # ==================== TRAVEL & HOSPITALITY ====================
    "hotel": {
        "name": "Hotel Management System",
        "entities": [
            Entity("Room", "Rooms", [
                ("number", "string"), ("type", "enum:single,double,deluxe,suite,presidential"),
                ("floor", "number"), ("price", "decimal"), ("capacity", "number"),
                ("amenities", "json"), ("images", "json"),
                ("status", "enum:available,occupied,maintenance,cleaning")
            ]),
            Entity("Guest", "Guests", [
                ("name", "string"), ("email", "string"), ("phone", "string"),
                ("idType", "string"), ("idNumber", "string"), ("nationality", "string"),
                ("vipStatus", "boolean"), ("preferences", "json")
            ]),
            Entity("HotelBooking", "HotelBookings", [
                ("bookingNumber", "string"), ("checkIn", "date"), ("checkOut", "date"),
                ("adults", "number"), ("children", "number"),
                ("roomRate", "decimal"), ("total", "decimal"),
                ("status", "enum:confirmed,checkedin,checkedout,cancelled,noshow"),
                ("specialRequests", "text"), ("source", "string")
            ]),
            Entity("Housekeeping", "Housekeepings", [
                ("type", "enum:cleaning,turndown,maintenance"),
                ("status", "enum:pending,inprogress,completed"),
                ("priority", "enum:normal,rush"), ("notes", "text")
            ]),
            Entity("RoomService", "RoomServices", [
                ("items", "json"), ("total", "decimal"),
                ("status", "enum:ordered,preparing,delivered"),
                ("instructions", "text")
            ]),
        ]
    },

    "travel_booking": {
        "name": "Travel Booking Platform",
        "entities": [
            Entity("Flight", "Flights", [
                ("flightNumber", "string"), ("airline", "string"),
                ("origin", "string"), ("destination", "string"),
                ("departure", "datetime"), ("arrival", "datetime"),
                ("duration", "number"), ("stops", "number"),
                ("price", "decimal"), ("class", "enum:economy,premium,business,first"),
                ("seatsAvailable", "number")
            ]),
            Entity("FlightBooking", "FlightBookings", [
                ("pnr", "string"), ("passengers", "json"), ("segments", "json"),
                ("totalFare", "decimal"), ("status", "enum:confirmed,cancelled,completed"),
                ("seatSelection", "json"), ("mealPreference", "string")
            ]),
            Entity("Hotel", "Hotels", [
                ("name", "string"), ("address", "text"), ("city", "string"),
                ("starRating", "number"), ("amenities", "json"),
                ("images", "json"), ("priceFrom", "decimal"), ("rating", "decimal")
            ]),
            Entity("TravelPackage", "TravelPackages", [
                ("name", "string"), ("description", "text"), ("destinations", "json"),
                ("duration", "number"), ("inclusions", "json"),
                ("price", "decimal"), ("itinerary", "json")
            ]),
            Entity("TravelInsurance", "TravelInsurances", [
                ("type", "string"), ("coverage", "json"), ("premium", "decimal"),
                ("startDate", "date"), ("endDate", "date")
            ]),
        ]
    },

    # ==================== EVENTS & ENTERTAINMENT ====================
    "event_management": {
        "name": "Event Management Platform",
        "entities": [
            Entity("Event", "Events", [
                ("title", "string"), ("description", "text"),
                ("type", "enum:conference,workshop,concert,exhibition,wedding,corporate"),
                ("startDate", "datetime"), ("endDate", "datetime"),
                ("venue", "string"), ("capacity", "number"),
                ("ticketPrice", "decimal"), ("banner", "string"),
                ("status", "enum:draft,published,ongoing,completed,cancelled")
            ]),
            Entity("Ticket", "Tickets", [
                ("ticketNumber", "string"), ("type", "enum:general,vip,early_bird,group"),
                ("price", "decimal"), ("quantity", "number"),
                ("status", "enum:available,sold,checkedin,cancelled"),
                ("qrCode", "string")
            ]),
            Entity("Venue", "Venues", [
                ("name", "string"), ("address", "text"), ("capacity", "number"),
                ("amenities", "json"), ("pricePerHour", "decimal"),
                ("images", "json"), ("availability", "json")
            ]),
            Entity("Speaker", "Speakers", [
                ("name", "string"), ("bio", "text"), ("photo", "string"),
                ("designation", "string"), ("company", "string"),
                ("socialLinks", "json")
            ]),
            Entity("Sponsor", "Sponsors", [
                ("name", "string"), ("logo", "string"), ("website", "string"),
                ("tier", "enum:platinum,gold,silver,bronze"),
                ("amount", "decimal"), ("benefits", "json")
            ]),
            Entity("Attendee", "Attendees", [
                ("name", "string"), ("email", "string"), ("phone", "string"),
                ("organization", "string"), ("dietaryPreference", "string"),
                ("checkedInAt", "datetime")
            ]),
        ]
    },

    "ticketing": {
        "name": "Ticket Booking System",
        "entities": [
            Entity("Show", "Shows", [
                ("title", "string"), ("type", "enum:movie,concert,play,sports,standup"),
                ("venue", "string"), ("date", "date"), ("time", "string"),
                ("duration", "number"), ("language", "string"),
                ("poster", "string"), ("description", "text")
            ]),
            Entity("Seat", "Seats", [
                ("row", "string"), ("number", "number"), ("category", "string"),
                ("price", "decimal"), ("status", "enum:available,booked,blocked")
            ]),
            Entity("TicketBooking", "TicketBookings", [
                ("bookingId", "string"), ("seats", "json"), ("totalAmount", "decimal"),
                ("status", "enum:confirmed,cancelled,used"),
                ("qrCode", "string"), ("validUntil", "datetime")
            ]),
        ]
    },

    # ==================== SOCIAL & COMMUNICATION ====================
    "social_network": {
        "name": "Social Network Platform",
        "entities": [
            Entity("Profile", "Profiles", [
                ("username", "string"), ("displayName", "string"), ("bio", "text"),
                ("avatar", "string"), ("coverPhoto", "string"),
                ("followers", "number"), ("following", "number"),
                ("isVerified", "boolean"), ("isPrivate", "boolean")
            ]),
            Entity("Post", "Posts", [
                ("content", "text"), ("media", "json"),
                ("likes", "number"), ("comments", "number"), ("shares", "number"),
                ("visibility", "enum:public,friends,private"),
                ("location", "string"), ("hashtags", "json")
            ]),
            Entity("Comment", "Comments", [
                ("content", "text"), ("likes", "number"), ("replies", "number")
            ]),
            Entity("Story", "Stories", [
                ("mediaUrl", "string"), ("mediaType", "enum:image,video"),
                ("views", "number"), ("expiresAt", "datetime")
            ]),
            Entity("Message", "Messages", [
                ("content", "text"), ("media", "json"),
                ("isRead", "boolean"), ("sentAt", "datetime"),
                ("readAt", "datetime")
            ]),
            Entity("Notification", "Notifications", [
                ("type", "string"), ("title", "string"), ("body", "text"),
                ("isRead", "boolean"), ("link", "string")
            ]),
        ]
    },

    "forum": {
        "name": "Community Forum Platform",
        "entities": [
            Entity("ForumCategory", "ForumCategories", [
                ("name", "string"), ("description", "text"), ("icon", "string"),
                ("order", "number"), ("topicCount", "number")
            ]),
            Entity("Topic", "Topics", [
                ("title", "string"), ("content", "text"),
                ("isPinned", "boolean"), ("isLocked", "boolean"),
                ("views", "number"), ("replies", "number"),
                ("lastActivity", "datetime")
            ]),
            Entity("Reply", "Replies", [
                ("content", "text"), ("likes", "number"),
                ("isAcceptedAnswer", "boolean")
            ]),
            Entity("Tag", "Tags", [
                ("name", "string"), ("description", "text"), ("usageCount", "number")
            ]),
        ]
    },

    # ==================== PROJECT & TASK MANAGEMENT ====================
    "project_management": {
        "name": "Project Management Tool",
        "entities": [
            Entity("Project", "Projects", [
                ("name", "string"), ("description", "text"), ("key", "string"),
                ("status", "enum:planning,active,onhold,completed,archived"),
                ("startDate", "date"), ("endDate", "date"),
                ("budget", "decimal"), ("progress", "number")
            ]),
            Entity("Task", "Tasks", [
                ("title", "string"), ("description", "text"),
                ("status", "enum:backlog,todo,inprogress,review,done"),
                ("priority", "enum:low,medium,high,critical"),
                ("type", "enum:feature,bug,task,story,epic"),
                ("dueDate", "date"), ("estimatedHours", "number"),
                ("actualHours", "number"), ("labels", "json")
            ]),
            Entity("Sprint", "Sprints", [
                ("name", "string"), ("goal", "text"),
                ("startDate", "date"), ("endDate", "date"),
                ("status", "enum:planning,active,completed"),
                ("velocity", "number")
            ]),
            Entity("Milestone", "Milestones", [
                ("name", "string"), ("description", "text"),
                ("dueDate", "date"), ("progress", "number"),
                ("status", "enum:pending,completed,overdue")
            ]),
            Entity("TimeLog", "TimeLogs", [
                ("description", "text"), ("hours", "decimal"),
                ("date", "date"), ("billable", "boolean")
            ]),
            Entity("Comment", "Comments", [
                ("content", "text"), ("attachments", "json")
            ]),
        ]
    },

    "helpdesk": {
        "name": "Helpdesk & Support System",
        "entities": [
            Entity("Ticket", "Tickets", [
                ("ticketNumber", "string"), ("subject", "string"), ("description", "text"),
                ("category", "string"), ("priority", "enum:low,medium,high,critical"),
                ("status", "enum:open,assigned,inprogress,pending,resolved,closed"),
                ("assignee", "uuid"), ("dueDate", "datetime")
            ]),
            Entity("TicketReply", "TicketReplies", [
                ("content", "text"), ("attachments", "json"),
                ("isInternal", "boolean")
            ]),
            Entity("KnowledgeArticle", "KnowledgeArticles", [
                ("title", "string"), ("content", "text"), ("category", "string"),
                ("views", "number"), ("helpful", "number"), ("notHelpful", "number"),
                ("status", "enum:draft,published,archived")
            ]),
            Entity("SLA", "SLAs", [
                ("name", "string"), ("responseTime", "number"), ("resolutionTime", "number"),
                ("priority", "string"), ("isActive", "boolean")
            ]),
        ]
    },

    # ==================== CRM & SALES ====================
    "crm": {
        "name": "CRM System",
        "entities": [
            Entity("Lead", "Leads", [
                ("name", "string"), ("email", "string"), ("phone", "string"),
                ("company", "string"), ("source", "enum:website,referral,social,advertisement,cold_call"),
                ("status", "enum:new,contacted,qualified,proposal,negotiation,won,lost"),
                ("value", "decimal"), ("notes", "text")
            ]),
            Entity("Contact", "Contacts", [
                ("name", "string"), ("email", "string"), ("phone", "string"),
                ("designation", "string"), ("company", "string"),
                ("address", "text"), ("tags", "json")
            ]),
            Entity("Company", "Companies", [
                ("name", "string"), ("industry", "string"), ("website", "string"),
                ("employees", "string"), ("revenue", "string"),
                ("address", "text")
            ]),
            Entity("Deal", "Deals", [
                ("title", "string"), ("value", "decimal"),
                ("stage", "enum:prospecting,qualification,proposal,negotiation,closed_won,closed_lost"),
                ("probability", "number"), ("expectedCloseDate", "date"),
                ("notes", "text")
            ]),
            Entity("Activity", "Activities", [
                ("type", "enum:call,email,meeting,task,note"),
                ("subject", "string"), ("description", "text"),
                ("scheduledAt", "datetime"), ("completedAt", "datetime"),
                ("outcome", "text")
            ]),
            Entity("Quote", "Quotes", [
                ("quoteNumber", "string"), ("items", "json"),
                ("subtotal", "decimal"), ("discount", "decimal"),
                ("tax", "decimal"), ("total", "decimal"),
                ("validUntil", "date"), ("status", "enum:draft,sent,accepted,rejected")
            ]),
        ]
    },

    # ==================== SUBSCRIPTION & SAAS ====================
    "subscription": {
        "name": "SaaS Subscription Platform",
        "entities": [
            Entity("Plan", "Plans", [
                ("name", "string"), ("description", "text"),
                ("price", "decimal"), ("billingCycle", "enum:monthly,quarterly,yearly"),
                ("features", "json"), ("limits", "json"),
                ("trialDays", "number"), ("isActive", "boolean")
            ]),
            Entity("Subscription", "Subscriptions", [
                ("status", "enum:trialing,active,past_due,cancelled,expired"),
                ("startDate", "date"), ("endDate", "date"),
                ("trialEndDate", "date"), ("autoRenew", "boolean"),
                ("cancelledAt", "datetime"), ("cancelReason", "text")
            ]),
            Entity("Invoice", "Invoices", [
                ("invoiceNumber", "string"), ("amount", "decimal"),
                ("tax", "decimal"), ("total", "decimal"),
                ("status", "enum:draft,pending,paid,overdue,void"),
                ("dueDate", "date"), ("paidAt", "datetime")
            ]),
            Entity("Usage", "Usages", [
                ("metric", "string"), ("quantity", "number"),
                ("timestamp", "datetime"), ("billable", "boolean")
            ]),
            Entity("Feature", "Features", [
                ("name", "string"), ("code", "string"),
                ("description", "text"), ("isAddon", "boolean"),
                ("price", "decimal")
            ]),
        ]
    },

    # ==================== MANUFACTURING ====================
    "manufacturing": {
        "name": "Manufacturing ERP",
        "entities": [
            Entity("RawMaterial", "RawMaterials", [
                ("name", "string"), ("sku", "string"), ("unit", "string"),
                ("stock", "number"), ("reorderLevel", "number"),
                ("unitCost", "decimal"), ("supplier", "uuid")
            ]),
            Entity("Product", "Products", [
                ("name", "string"), ("sku", "string"), ("description", "text"),
                ("bom", "json"), ("productionTime", "number"),
                ("costPrice", "decimal"), ("sellingPrice", "decimal")
            ]),
            Entity("WorkOrder", "WorkOrders", [
                ("orderNumber", "string"), ("product", "uuid"), ("quantity", "number"),
                ("status", "enum:planned,inprogress,completed,cancelled"),
                ("startDate", "date"), ("dueDate", "date")
            ]),
            Entity("Machine", "Machines", [
                ("name", "string"), ("type", "string"), ("location", "string"),
                ("status", "enum:running,idle,maintenance,breakdown"),
                ("lastMaintenance", "date"), ("nextMaintenance", "date")
            ]),
            Entity("QualityCheck", "QualityChecks", [
                ("parameters", "json"), ("result", "enum:pass,fail,hold"),
                ("inspector", "uuid"), ("notes", "text")
            ]),
        ]
    },

    # ==================== AGRICULTURE ====================
    "agriculture": {
        "name": "Agriculture Management System",
        "entities": [
            Entity("Farm", "Farms", [
                ("name", "string"), ("location", "text"), ("area", "decimal"),
                ("cropTypes", "json"), ("soilType", "string")
            ]),
            Entity("Crop", "Crops", [
                ("name", "string"), ("variety", "string"), ("season", "string"),
                ("plantingDate", "date"), ("harvestDate", "date"),
                ("expectedYield", "decimal"), ("actualYield", "decimal")
            ]),
            Entity("Field", "Fields", [
                ("name", "string"), ("area", "decimal"), ("soilType", "string"),
                ("irrigationType", "string"), ("currentCrop", "uuid")
            ]),
            Entity("Harvest", "Harvests", [
                ("date", "date"), ("quantity", "decimal"), ("quality", "string"),
                ("price", "decimal"), ("buyer", "string")
            ]),
            Entity("Equipment", "Equipments", [
                ("name", "string"), ("type", "string"),
                ("status", "enum:available,inuse,maintenance"),
                ("lastService", "date")
            ]),
        ]
    },

    # ==================== FITNESS & WELLNESS ====================
    "gym": {
        "name": "Gym & Fitness Center",
        "entities": [
            Entity("Member", "Members", [
                ("name", "string"), ("email", "string"), ("phone", "string"),
                ("membershipType", "enum:basic,standard,premium,vip"),
                ("startDate", "date"), ("endDate", "date"),
                ("height", "decimal"), ("weight", "decimal"),
                ("fitnessGoal", "string")
            ]),
            Entity("Trainer", "Trainers", [
                ("name", "string"), ("email", "string"), ("specialization", "json"),
                ("certifications", "json"), ("experience", "number"),
                ("rating", "decimal"), ("hourlyRate", "decimal")
            ]),
            Entity("Workout", "Workouts", [
                ("name", "string"), ("type", "enum:cardio,strength,flexibility,hiit,yoga"),
                ("duration", "number"), ("calories", "number"),
                ("difficulty", "enum:beginner,intermediate,advanced"),
                ("exercises", "json")
            ]),
            Entity("ClassSchedule", "ClassSchedules", [
                ("name", "string"), ("trainer", "uuid"), ("dayOfWeek", "string"),
                ("startTime", "string"), ("duration", "number"),
                ("capacity", "number"), ("enrolled", "number")
            ]),
            Entity("PTSession", "PTSessions", [
                ("scheduledAt", "datetime"), ("duration", "number"),
                ("status", "enum:scheduled,completed,cancelled"),
                ("notes", "text"), ("feedback", "text")
            ]),
            Entity("BodyMetric", "BodyMetrics", [
                ("date", "date"), ("weight", "decimal"), ("bodyFat", "decimal"),
                ("muscleMass", "decimal"), ("bmi", "decimal")
            ]),
        ]
    },

    # ==================== AUTOMOTIVE ====================
    "car_dealership": {
        "name": "Car Dealership Management",
        "entities": [
            Entity("Vehicle", "Vehicles", [
                ("make", "string"), ("model", "string"), ("year", "number"),
                ("vin", "string"), ("color", "string"), ("mileage", "number"),
                ("fuelType", "enum:petrol,diesel,electric,hybrid"),
                ("transmission", "enum:manual,automatic"),
                ("price", "decimal"), ("status", "enum:available,sold,reserved")
            ]),
            Entity("TestDrive", "TestDrives", [
                ("scheduledAt", "datetime"), ("duration", "number"),
                ("status", "enum:scheduled,completed,cancelled"),
                ("feedback", "text"), ("interested", "boolean")
            ]),
            Entity("SalesInquiry", "SalesInquiries", [
                ("name", "string"), ("email", "string"), ("phone", "string"),
                ("interestedIn", "uuid"), ("budget", "decimal"),
                ("status", "enum:new,contacted,negotiation,closed")
            ]),
            Entity("VehicleSale", "VehicleSales", [
                ("salePrice", "decimal"), ("downPayment", "decimal"),
                ("financingType", "enum:cash,loan,lease"),
                ("documents", "json"), ("deliveryDate", "date")
            ]),
        ]
    },

    "service_center": {
        "name": "Vehicle Service Center",
        "entities": [
            Entity("ServiceVehicle", "ServiceVehicles", [
                ("make", "string"), ("model", "string"), ("year", "number"),
                ("registrationNumber", "string"), ("vin", "string"),
                ("lastService", "date"), ("nextServiceDue", "date")
            ]),
            Entity("ServiceBooking", "ServiceBookings", [
                ("scheduledAt", "datetime"), ("type", "enum:regular,repair,inspection,bodywork"),
                ("status", "enum:scheduled,inprogress,completed,cancelled"),
                ("estimatedCost", "decimal"), ("actualCost", "decimal")
            ]),
            Entity("ServiceJob", "ServiceJobs", [
                ("description", "text"), ("parts", "json"), ("labor", "decimal"),
                ("status", "enum:pending,inprogress,completed"),
                ("technician", "uuid")
            ]),
            Entity("SparePart", "SpareParts", [
                ("name", "string"), ("partNumber", "string"), ("price", "decimal"),
                ("stock", "number"), ("reorderLevel", "number")
            ]),
        ]
    },

    # ==================== LEGAL ====================
    "law_firm": {
        "name": "Law Firm Management",
        "entities": [
            Entity("Client", "Clients", [
                ("name", "string"), ("email", "string"), ("phone", "string"),
                ("type", "enum:individual,corporate"), ("address", "text")
            ]),
            Entity("Case", "Cases", [
                ("caseNumber", "string"), ("title", "string"), ("type", "string"),
                ("status", "enum:open,inprogress,pending,closed,won,lost"),
                ("filingDate", "date"), ("nextHearing", "datetime"),
                ("description", "text")
            ]),
            Entity("Document", "Documents", [
                ("title", "string"), ("type", "string"), ("fileUrl", "string"),
                ("version", "number"), ("status", "enum:draft,review,final")
            ]),
            Entity("TimeEntry", "TimeEntries", [
                ("description", "text"), ("hours", "decimal"), ("rate", "decimal"),
                ("billable", "boolean"), ("date", "date")
            ]),
            Entity("Invoice", "Invoices", [
                ("invoiceNumber", "string"), ("items", "json"), ("total", "decimal"),
                ("status", "enum:draft,sent,paid,overdue")
            ]),
        ]
    },

    # ==================== LIBRARY ====================
    "library": {
        "name": "Library Management System",
        "entities": [
            Entity("Book", "Books", [
                ("title", "string"), ("isbn", "string"), ("author", "string"),
                ("publisher", "string"), ("category", "string"),
                ("copies", "number"), ("available", "number"),
                ("location", "string")
            ]),
            Entity("LibraryMember", "LibraryMembers", [
                ("name", "string"), ("email", "string"), ("phone", "string"),
                ("membershipId", "string"), ("membershipType", "enum:student,faculty,public"),
                ("expiryDate", "date")
            ]),
            Entity("BookIssue", "BookIssues", [
                ("issueDate", "date"), ("dueDate", "date"), ("returnDate", "date"),
                ("status", "enum:issued,returned,overdue,lost"),
                ("fine", "decimal")
            ]),
            Entity("Reservation", "Reservations", [
                ("reservedAt", "datetime"), ("status", "enum:waiting,available,cancelled,completed"),
                ("notifiedAt", "datetime")
            ]),
        ]
    },

    # ==================== PARKING ====================
    "parking": {
        "name": "Parking Management System",
        "entities": [
            Entity("ParkingLot", "ParkingLots", [
                ("name", "string"), ("address", "text"), ("totalSpots", "number"),
                ("availableSpots", "number"), ("hourlyRate", "decimal"),
                ("operatingHours", "json")
            ]),
            Entity("ParkingSpot", "ParkingSpots", [
                ("spotNumber", "string"), ("floor", "number"),
                ("type", "enum:regular,compact,handicap,ev"),
                ("status", "enum:available,occupied,reserved,maintenance")
            ]),
            Entity("ParkingSession", "ParkingSessions", [
                ("entryTime", "datetime"), ("exitTime", "datetime"),
                ("vehicleNumber", "string"), ("amount", "decimal"),
                ("paymentStatus", "enum:pending,paid")
            ]),
            Entity("MonthlyPass", "MonthlyPasses", [
                ("vehicleNumber", "string"), ("startDate", "date"),
                ("endDate", "date"), ("amount", "decimal"),
                ("status", "enum:active,expired")
            ]),
        ]
    },

    # ==================== VETERINARY ====================
    "veterinary": {
        "name": "Veterinary Clinic Management",
        "entities": [
            Entity("Pet", "Pets", [
                ("name", "string"), ("species", "enum:dog,cat,bird,rabbit,other"),
                ("breed", "string"), ("age", "number"), ("weight", "decimal"),
                ("gender", "enum:male,female"), ("medicalHistory", "json")
            ]),
            Entity("PetOwner", "PetOwners", [
                ("name", "string"), ("email", "string"), ("phone", "string"),
                ("address", "text")
            ]),
            Entity("Veterinarian", "Veterinarians", [
                ("name", "string"), ("email", "string"), ("specialization", "string"),
                ("license", "string"), ("experience", "number")
            ]),
            Entity("VetAppointment", "VetAppointments", [
                ("scheduledAt", "datetime"), ("reason", "text"),
                ("status", "enum:scheduled,completed,cancelled"),
                ("diagnosis", "text"), ("treatment", "text")
            ]),
            Entity("Vaccination", "Vaccinations", [
                ("vaccine", "string"), ("date", "date"), ("nextDue", "date"),
                ("batch", "string"), ("administeredBy", "uuid")
            ]),
        ]
    },

    # ==================== LAUNDRY ====================
    "laundry": {
        "name": "Laundry & Dry Cleaning",
        "entities": [
            Entity("LaundryOrder", "LaundryOrders", [
                ("orderNumber", "string"), ("items", "json"),
                ("services", "json"), ("total", "decimal"),
                ("status", "enum:received,processing,ready,delivered"),
                ("pickupDate", "date"), ("deliveryDate", "date")
            ]),
            Entity("LaundryItem", "LaundryItems", [
                ("name", "string"), ("category", "string"),
                ("washPrice", "decimal"), ("ironPrice", "decimal"),
                ("dryCleanPrice", "decimal")
            ]),
            Entity("LaundryCustomer", "LaundryCustomers", [
                ("name", "string"), ("phone", "string"), ("address", "text"),
                ("preferences", "json")
            ]),
        ]
    },

    # ==================== SALON ====================
    "salon": {
        "name": "Salon & Spa Management",
        "entities": [
            Entity("SalonService", "SalonServices", [
                ("name", "string"), ("category", "string"), ("description", "text"),
                ("duration", "number"), ("price", "decimal")
            ]),
            Entity("Stylist", "Stylists", [
                ("name", "string"), ("email", "string"), ("phone", "string"),
                ("specializations", "json"), ("rating", "decimal"),
                ("availability", "json")
            ]),
            Entity("SalonAppointment", "SalonAppointments", [
                ("scheduledAt", "datetime"), ("services", "json"),
                ("status", "enum:scheduled,confirmed,inprogress,completed,cancelled"),
                ("total", "decimal"), ("notes", "text")
            ]),
            Entity("SalonClient", "SalonClients", [
                ("name", "string"), ("email", "string"), ("phone", "string"),
                ("preferences", "json"), ("allergies", "text")
            ]),
        ]
    },
}


# ============================================================================
# CODE GENERATION TEMPLATES
# ============================================================================

def generate_react_form(entity: Entity, domain_name: str) -> str:
    """Generate React form component"""
    attrs = entity.attributes[:8]
    entity_lower = entity.name[0].lower() + entity.name[1:]

    form_fields = []
    schema_fields = []

    for attr_name, attr_type in attrs:
        label = attr_name.replace("_", " ").title()
        if "id" in attr_name.lower() or attr_name == "id":
            continue

        if attr_type == "string":
            schema_fields.append(f'  {attr_name}: z.string().min(1, "{label} is required"),')
            form_fields.append(f'''
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
            <input {{...register("{attr_name}")}} type="text" className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500" />
            {{errors.{attr_name} && <p className="text-red-500 text-sm mt-1">{{errors.{attr_name}.message}}</p>}}
          </div>''')

        elif attr_type == "text":
            schema_fields.append(f'  {attr_name}: z.string().optional(),')
            form_fields.append(f'''
          <div className="col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
            <textarea {{...register("{attr_name}")}} rows={{4}} className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500" />
          </div>''')

        elif attr_type in ["number", "decimal"]:
            schema_fields.append(f'  {attr_name}: z.number().min(0),')
            form_fields.append(f'''
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
            <input {{...register("{attr_name}", {{ valueAsNumber: true }})}} type="number" step="any" className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500" />
          </div>''')

        elif attr_type == "boolean":
            schema_fields.append(f'  {attr_name}: z.boolean().default(false),')
            form_fields.append(f'''
          <div className="flex items-center">
            <input {{...register("{attr_name}")}} type="checkbox" className="w-4 h-4 text-blue-600 rounded" />
            <label className="ml-2 text-sm text-gray-700">{label}</label>
          </div>''')

        elif attr_type == "date":
            schema_fields.append(f'  {attr_name}: z.string(),')
            form_fields.append(f'''
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
            <input {{...register("{attr_name}")}} type="date" className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500" />
          </div>''')

        elif attr_type == "datetime":
            schema_fields.append(f'  {attr_name}: z.string(),')
            form_fields.append(f'''
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
            <input {{...register("{attr_name}")}} type="datetime-local" className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500" />
          </div>''')

        elif attr_type.startswith("enum:"):
            options = attr_type.replace("enum:", "").split(",")
            opts_str = ", ".join([f'"{o}"' for o in options])
            schema_fields.append(f'  {attr_name}: z.enum([{opts_str}]),')
            opts = "\n".join([f'              <option value="{o}">{o.replace("_", " ").title()}</option>' for o in options])
            form_fields.append(f'''
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
            <select {{...register("{attr_name}")}} className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500">
              <option value="">Select {label}</option>
{opts}
            </select>
          </div>''')

    return f'''```tsx
import React from 'react';
import {{ useForm }} from 'react-hook-form';
import {{ zodResolver }} from '@hookform/resolvers/zod';
import {{ z }} from 'zod';
import {{ Loader2 }} from 'lucide-react';

const {entity_lower}Schema = z.object({{
{chr(10).join(schema_fields)}
}});

type {entity.name}FormData = z.infer<typeof {entity_lower}Schema>;

interface {entity.name}FormProps {{
  initialData?: Partial<{entity.name}FormData>;
  onSubmit: (data: {entity.name}FormData) => Promise<void>;
  isEdit?: boolean;
}}

export default function {entity.name}Form({{ initialData, onSubmit, isEdit = false }}: {entity.name}FormProps) {{
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  const {{ register, handleSubmit, formState: {{ errors }} }} = useForm<{entity.name}FormData>({{
    resolver: zodResolver({entity_lower}Schema),
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
    <form onSubmit={{handleSubmit(handleFormSubmit)}} className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {chr(10).join(form_fields)}
      </div>

      <div className="flex justify-end space-x-4">
        <button type="button" className="px-4 py-2 border rounded-lg hover:bg-gray-50">
          Cancel
        </button>
        <button
          type="submit"
          disabled={{isSubmitting}}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center"
        >
          {{isSubmitting && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}}
          {{isEdit ? 'Update' : 'Create'}} {entity.name}
        </button>
      </div>
    </form>
  );
}}
```'''


def generate_react_list(entity: Entity, domain_name: str) -> str:
    """Generate React list/table component"""
    display_attrs = [(n, t) for n, t in entity.attributes[:6] if "id" not in n.lower() and t != "json" and t != "text"]

    headers = "\n".join([f'              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{a[0].replace("_", " ").title()}</th>' for a in display_attrs])
    cells = "\n".join([f'                <td className="px-4 py-3 text-sm text-gray-900">{{item.{a[0]}}}</td>' for a in display_attrs])

    return f'''```tsx
import React from 'react';
import {{ useQuery }} from '@tanstack/react-query';
import {{ Plus, Search, Edit2, Trash2, Loader2 }} from 'lucide-react';

interface {entity.name} {{
  id: string;
{chr(10).join([f"  {a[0]}: {'string' if a[1] in ['string', 'text', 'date', 'datetime'] or a[1].startswith('enum') else 'number' if a[1] in ['number', 'decimal'] else 'boolean' if a[1] == 'boolean' else 'any'};" for a in display_attrs])}
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
    queryFn: () => fetch(`/api/{entity.plural.lower()}?page=${{page}}&search=${{search}}`).then(r => r.json()),
  }});

  if (isLoading) {{
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }}

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="p-4 border-b flex justify-between items-center">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search..."
            value={{search}}
            onChange={{(e) => setSearch(e.target.value)}}
            className="pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
          />
        </div>
        {{onCreate && (
          <button onClick={{onCreate}} className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            <Plus className="w-5 h-5 mr-2" /> Add {entity.name}
          </button>
        )}}
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
{headers}
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {{data?.items?.map((item: {entity.name}) => (
              <tr key={{item.id}} className="hover:bg-gray-50">
{cells}
                <td className="px-4 py-3 text-right">
                  <button onClick={{() => onEdit?.(item)}} className="text-blue-600 hover:text-blue-900 mr-2">
                    <Edit2 className="w-4 h-4" />
                  </button>
                  <button onClick={{() => onDelete?.(item.id)}} className="text-red-600 hover:text-red-900">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            ))}}
          </tbody>
        </table>
      </div>

      <div className="p-4 border-t flex justify-between items-center">
        <span className="text-sm text-gray-500">
          Showing {{data?.items?.length || 0}} of {{data?.total || 0}}
        </span>
        <div className="flex space-x-2">
          <button onClick={{() => setPage(p => Math.max(1, p - 1))}} disabled={{page === 1}} className="px-3 py-1 border rounded disabled:opacity-50">
            Previous
          </button>
          <button onClick={{() => setPage(p => p + 1)}} disabled={{!data?.hasMore}} className="px-3 py-1 border rounded disabled:opacity-50">
            Next
          </button>
        </div>
      </div>
    </div>
  );
}}
```'''


def generate_fastapi_crud(entity: Entity, domain_name: str) -> str:
    """Generate FastAPI CRUD endpoints"""
    entity_lower = entity.name[0].lower() + entity.name[1:]
    entity_plural_lower = entity.plural[0].lower() + entity.plural[1:]

    return f'''```python
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.{entity_lower} import {entity.name}
from app.schemas.{entity_lower} import {entity.name}Create, {entity.name}Update, {entity.name}Response

router = APIRouter(prefix="/{entity_plural_lower}", tags=["{entity.plural}"])


@router.get("/", response_model=dict)
async def list_{entity_plural_lower}(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """List all {entity_plural_lower} with pagination and search"""
    query = db.query({entity.name})

    if search:
        query = query.filter(
            or_(
                {entity.name}.name.ilike(f"%{{search}}%") if hasattr({entity.name}, 'name') else True,
            )
        )

    total = query.count()
    items = query.offset((page - 1) * limit).limit(limit).all()

    return {{
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "hasMore": (page * limit) < total
    }}


@router.get("/{{id}}", response_model={entity.name}Response)
async def get_{entity_lower}(
    id: UUID,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Get {entity_lower} by ID"""
    {entity_lower} = db.query({entity.name}).filter({entity.name}.id == id).first()
    if not {entity_lower}:
        raise HTTPException(status_code=404, detail="{entity.name} not found")
    return {entity_lower}


@router.post("/", response_model={entity.name}Response, status_code=status.HTTP_201_CREATED)
async def create_{entity_lower}(
    data: {entity.name}Create,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Create new {entity_lower}"""
    {entity_lower} = {entity.name}(**data.model_dump())
    db.add({entity_lower})
    db.commit()
    db.refresh({entity_lower})
    return {entity_lower}


@router.put("/{{id}}", response_model={entity.name}Response)
async def update_{entity_lower}(
    id: UUID,
    data: {entity.name}Update,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Update {entity_lower}"""
    {entity_lower} = db.query({entity.name}).filter({entity.name}.id == id).first()
    if not {entity_lower}:
        raise HTTPException(status_code=404, detail="{entity.name} not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr({entity_lower}, field, value)

    db.commit()
    db.refresh({entity_lower})
    return {entity_lower}


@router.delete("/{{id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_{entity_lower}(
    id: UUID,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Delete {entity_lower}"""
    {entity_lower} = db.query({entity.name}).filter({entity.name}.id == id).first()
    if not {entity_lower}:
        raise HTTPException(status_code=404, detail="{entity.name} not found")

    db.delete({entity_lower})
    db.commit()
```'''


def generate_sqlalchemy_model(entity: Entity, domain_name: str) -> str:
    """Generate SQLAlchemy model"""
    entity_plural_lower = entity.plural[0].lower() + entity.plural[1:]

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

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<{entity.name} {{self.id}}>"
```'''


def generate_pydantic_schema(entity: Entity, domain_name: str) -> str:
    """Generate Pydantic schemas"""
    fields = []
    optional_fields = []

    for attr_name, attr_type in entity.attributes:
        if attr_type == "string":
            fields.append(f'    {attr_name}: str')
            optional_fields.append(f'    {attr_name}: Optional[str] = None')
        elif attr_type == "text":
            fields.append(f'    {attr_name}: Optional[str] = None')
            optional_fields.append(f'    {attr_name}: Optional[str] = None')
        elif attr_type in ["number", "decimal"]:
            fields.append(f'    {attr_name}: {"int" if attr_type == "number" else "float"}')
            optional_fields.append(f'    {attr_name}: Optional[{"int" if attr_type == "number" else "float"}] = None')
        elif attr_type == "boolean":
            fields.append(f'    {attr_name}: bool = False')
            optional_fields.append(f'    {attr_name}: Optional[bool] = None')
        elif attr_type == "date":
            fields.append(f'    {attr_name}: date')
            optional_fields.append(f'    {attr_name}: Optional[date] = None')
        elif attr_type == "datetime":
            fields.append(f'    {attr_name}: datetime')
            optional_fields.append(f'    {attr_name}: Optional[datetime] = None')
        elif attr_type == "json":
            fields.append(f'    {attr_name}: Dict[str, Any] = Field(default_factory=dict)')
            optional_fields.append(f'    {attr_name}: Optional[Dict[str, Any]] = None')
        elif attr_type.startswith("enum:"):
            fields.append(f'    {attr_name}: str')
            optional_fields.append(f'    {attr_name}: Optional[str] = None')
        elif attr_type == "uuid":
            fields.append(f'    {attr_name}: UUID')
            optional_fields.append(f'    {attr_name}: Optional[UUID] = None')

    return f'''```python
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, date


class {entity.name}Base(BaseModel):
{chr(10).join(fields[:8])}


class {entity.name}Create({entity.name}Base):
    pass


class {entity.name}Update(BaseModel):
{chr(10).join(optional_fields[:8])}


class {entity.name}Response({entity.name}Base):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
```'''


def generate_detail_page(entity: Entity, domain_name: str) -> str:
    """Generate React detail/view page"""
    display_attrs = [(n, t) for n, t in entity.attributes[:10] if t != "json"]

    fields = []
    for attr_name, attr_type in display_attrs:
        label = attr_name.replace("_", " ").title()
        fields.append(f'''
          <div>
            <dt className="text-sm font-medium text-gray-500">{label}</dt>
            <dd className="mt-1 text-sm text-gray-900">{{{entity.name.lower()}.{attr_name} || '-'}}</dd>
          </div>''')

    return f'''```tsx
import React from 'react';
import {{ useQuery }} from '@tanstack/react-query';
import {{ useParams, useNavigate }} from 'react-router-dom';
import {{ ArrowLeft, Edit2, Trash2, Loader2 }} from 'lucide-react';

interface {entity.name} {{
  id: string;
{chr(10).join([f"  {a[0]}: any;" for a in display_attrs])}
  createdAt: string;
  updatedAt: string;
}}

export default function {entity.name}Detail() {{
  const {{ id }} = useParams<{{ id: string }}>();
  const navigate = useNavigate();

  const {{ data: {entity.name.lower()}, isLoading }} = useQuery<{entity.name}>({{
    queryKey: ['{entity.plural.lower()}', id],
    queryFn: () => fetch(`/api/{entity.plural.lower()}/${{id}}`).then(r => r.json()),
  }});

  if (isLoading) {{
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }}

  if (!{entity.name.lower()}) {{
    return <div className="text-center py-8 text-gray-500">{entity.name} not found</div>;
  }}

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <button onClick={{() => navigate(-1)}} className="flex items-center text-gray-600 hover:text-gray-900">
          <ArrowLeft className="w-5 h-5 mr-2" /> Back
        </button>
        <div className="flex space-x-2">
          <button onClick={{() => navigate(`/{entity.plural.lower()}/${{id}}/edit`)}} className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            <Edit2 className="w-4 h-4 mr-2" /> Edit
          </button>
          <button className="flex items-center px-4 py-2 border border-red-600 text-red-600 rounded-lg hover:bg-red-50">
            <Trash2 className="w-4 h-4 mr-2" /> Delete
          </button>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b">
          <h1 className="text-2xl font-bold text-gray-900">{entity.name} Details</h1>
        </div>
        <div className="p-6">
          <dl className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {chr(10).join(fields)}
          </dl>
        </div>
      </div>
    </div>
  );
}}
```'''


# ============================================================================
# SAMPLE GENERATION
# ============================================================================

def generate_all_samples() -> List[Dict]:
    """Generate samples for all domains"""
    all_samples = []

    for domain_key, domain_config in DOMAINS.items():
        domain_name = domain_config["name"]
        print(f"Generating samples for {domain_name}...")

        for entity in domain_config["entities"]:
            # React Form
            all_samples.append({
                "messages": [
                    {"role": "system", "content": f"You are an expert full-stack developer building a {domain_name}."},
                    {"role": "user", "content": f"Create a React form component for {entity.name} with TypeScript, Tailwind CSS, react-hook-form, and Zod validation"},
                    {"role": "assistant", "content": generate_react_form(entity, domain_name)}
                ]
            })

            # React List
            all_samples.append({
                "messages": [
                    {"role": "system", "content": f"You are an expert full-stack developer building a {domain_name}."},
                    {"role": "user", "content": f"Create a React table/list component for {entity.plural} with search, pagination, and CRUD actions using TypeScript and Tailwind CSS"},
                    {"role": "assistant", "content": generate_react_list(entity, domain_name)}
                ]
            })

            # React Detail Page
            all_samples.append({
                "messages": [
                    {"role": "system", "content": f"You are an expert full-stack developer building a {domain_name}."},
                    {"role": "user", "content": f"Create a React detail/view page for {entity.name} with TypeScript and Tailwind CSS"},
                    {"role": "assistant", "content": generate_detail_page(entity, domain_name)}
                ]
            })

            # FastAPI CRUD
            all_samples.append({
                "messages": [
                    {"role": "system", "content": f"You are an expert Python backend developer building a {domain_name}."},
                    {"role": "user", "content": f"Create FastAPI CRUD endpoints for {entity.name} with pagination, search, and proper error handling"},
                    {"role": "assistant", "content": generate_fastapi_crud(entity, domain_name)}
                ]
            })

            # SQLAlchemy Model
            all_samples.append({
                "messages": [
                    {"role": "system", "content": f"You are an expert Python backend developer building a {domain_name}."},
                    {"role": "user", "content": f"Create a SQLAlchemy model for {entity.name} with all necessary fields and relationships"},
                    {"role": "assistant", "content": generate_sqlalchemy_model(entity, domain_name)}
                ]
            })

            # Pydantic Schema
            all_samples.append({
                "messages": [
                    {"role": "system", "content": f"You are an expert Python backend developer building a {domain_name}."},
                    {"role": "user", "content": f"Create Pydantic schemas for {entity.name} including Create, Update, and Response schemas"},
                    {"role": "assistant", "content": generate_pydantic_schema(entity, domain_name)}
                ]
            })

        entity_count = len(domain_config["entities"])
        print(f"  Generated {entity_count * 6} samples ({entity_count} entities x 6 sample types)")

    return all_samples


def save_samples(output_dir: str = "./data/comprehensive"):
    """Save all samples"""
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    samples = generate_all_samples()

    output_file = Path(output_dir) / "all_domains.jsonl"
    with open(output_file, "w", encoding="utf-8") as f:
        for sample in samples:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")

    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Total domains: {len(DOMAINS)}")
    total_entities = sum(len(d["entities"]) for d in DOMAINS.values())
    print(f"Total entities: {total_entities}")
    print(f"Total samples: {len(samples)}")
    print(f"Sample types per entity: 6 (Form, List, Detail, API, Model, Schema)")
    print(f"\nSaved to: {output_file}")

    return samples


if __name__ == "__main__":
    save_samples()
