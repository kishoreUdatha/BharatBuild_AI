"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/hooks/useAuth";
import { apiClient } from "@/lib/api-client";
import {
  MessageSquare,
  Bell,
  Send,
  Users,
  User,
  Clock,
  Plus,
  X,
  Search,
  Filter,
  ChevronRight,
  AlertCircle,
  CheckCircle,
  Megaphone,
  Mail,
} from "lucide-react";

interface Announcement {
  id: string;
  title: string;
  content: string;
  priority: "low" | "normal" | "high" | "urgent";
  target_type: string;
  target_name: string;
  created_at: string;
  read_count: number;
  total_recipients: number;
}

interface Message {
  id: string;
  student_id: string;
  student_name: string;
  content: string;
  sent_at: string;
  is_read: boolean;
  direction: "sent" | "received";
}

interface Student {
  id: string;
  name: string;
  roll_number: string;
  email: string;
  class_name: string;
}

export default function CommunicationPage() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<"announcements" | "messages">("announcements");
  const [loading, setLoading] = useState(true);
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [classes, setClasses] = useState<{ id: string; name: string }[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [showNewAnnouncement, setShowNewAnnouncement] = useState(false);
  const [showNewMessage, setShowNewMessage] = useState(false);
  const [selectedStudent, setSelectedStudent] = useState<Student | null>(null);
  const [studentSearch, setStudentSearch] = useState("");

  // Form states
  const [announcementForm, setAnnouncementForm] = useState({
    title: "",
    content: "",
    priority: "normal",
    target_type: "all",
    target_id: "",
  });
  const [messageContent, setMessageContent] = useState("");

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [announcementsRes, classesRes] = await Promise.all([
        apiClient.get("/faculty/announcements"),
        apiClient.get("/faculty/classes"),
      ]);
      setAnnouncements(announcementsRes.data || []);
      setClasses(classesRes.data || []);
    } catch (error) {
      console.error("Error fetching data:", error);
      // Demo data
      setAnnouncements([
        {
          id: "ann-1",
          title: "Lab Submission Deadline Extended",
          content:
            "The deadline for Data Structures Lab Assignment 3 has been extended to February 5th, 2026.",
          priority: "high",
          target_type: "class",
          target_name: "CSE-A (Sem 5)",
          created_at: new Date().toISOString(),
          read_count: 45,
          total_recipients: 60,
        },
        {
          id: "ann-2",
          title: "Project Review Schedule",
          content:
            "Project review for all final year students will be conducted on February 10th. Please prepare your presentations.",
          priority: "urgent",
          target_type: "all",
          target_name: "All Students",
          created_at: new Date(Date.now() - 86400000).toISOString(),
          read_count: 120,
          total_recipients: 180,
        },
        {
          id: "ann-3",
          title: "New Lab Topics Available",
          content: "New topics have been added to the DBMS Lab. Please check and start working on them.",
          priority: "normal",
          target_type: "class",
          target_name: "CSE-B (Sem 5)",
          created_at: new Date(Date.now() - 172800000).toISOString(),
          read_count: 30,
          total_recipients: 58,
        },
      ]);
      setClasses([
        { id: "cls-1", name: "CSE-A (Sem 5)" },
        { id: "cls-2", name: "CSE-B (Sem 5)" },
        { id: "cls-3", name: "CSE-A (Sem 3)" },
      ]);
    }

    // Demo messages
    setMessages([
      {
        id: "msg-1",
        student_id: "stu-1",
        student_name: "Rahul Kumar",
        content: "Sir, I have a doubt regarding the Binary Tree assignment.",
        sent_at: new Date(Date.now() - 3600000).toISOString(),
        is_read: true,
        direction: "received",
      },
      {
        id: "msg-2",
        student_id: "stu-1",
        student_name: "Rahul Kumar",
        content: "Sure, please explain your doubt in detail.",
        sent_at: new Date(Date.now() - 3500000).toISOString(),
        is_read: true,
        direction: "sent",
      },
      {
        id: "msg-3",
        student_id: "stu-2",
        student_name: "Priya Sharma",
        content: "Thank you for extending the deadline, Sir.",
        sent_at: new Date(Date.now() - 7200000).toISOString(),
        is_read: true,
        direction: "received",
      },
    ]);

    // Demo students
    setStudents([
      { id: "stu-1", name: "Rahul Kumar", roll_number: "20CS001", email: "rahul@college.edu", class_name: "CSE-A" },
      { id: "stu-2", name: "Priya Sharma", roll_number: "20CS002", email: "priya@college.edu", class_name: "CSE-A" },
      { id: "stu-3", name: "Amit Patel", roll_number: "20CS003", email: "amit@college.edu", class_name: "CSE-B" },
      { id: "stu-4", name: "Sneha Reddy", roll_number: "20CS004", email: "sneha@college.edu", class_name: "CSE-A" },
    ]);

    setLoading(false);
  };

  const createAnnouncement = async () => {
    try {
      await apiClient.post("/faculty/announcements", {
        title: announcementForm.title,
        content: announcementForm.content,
        priority: announcementForm.priority,
        department_id: announcementForm.target_type === "department" ? announcementForm.target_id : null,
      });

      // Add to local state
      const newAnnouncement: Announcement = {
        id: `ann-${Date.now()}`,
        title: announcementForm.title,
        content: announcementForm.content,
        priority: announcementForm.priority as any,
        target_type: announcementForm.target_type,
        target_name:
          announcementForm.target_type === "all"
            ? "All Students"
            : classes.find((c) => c.id === announcementForm.target_id)?.name || "Unknown",
        created_at: new Date().toISOString(),
        read_count: 0,
        total_recipients: announcementForm.target_type === "all" ? 180 : 60,
      };

      setAnnouncements([newAnnouncement, ...announcements]);
      setShowNewAnnouncement(false);
      setAnnouncementForm({
        title: "",
        content: "",
        priority: "normal",
        target_type: "all",
        target_id: "",
      });
    } catch (error) {
      console.error("Error creating announcement:", error);
      // Still add locally for demo
      const newAnnouncement: Announcement = {
        id: `ann-${Date.now()}`,
        title: announcementForm.title,
        content: announcementForm.content,
        priority: announcementForm.priority as any,
        target_type: announcementForm.target_type,
        target_name:
          announcementForm.target_type === "all"
            ? "All Students"
            : classes.find((c) => c.id === announcementForm.target_id)?.name || "Unknown",
        created_at: new Date().toISOString(),
        read_count: 0,
        total_recipients: announcementForm.target_type === "all" ? 180 : 60,
      };

      setAnnouncements([newAnnouncement, ...announcements]);
      setShowNewAnnouncement(false);
      setAnnouncementForm({
        title: "",
        content: "",
        priority: "normal",
        target_type: "all",
        target_id: "",
      });
    }
  };

  const sendMessage = async () => {
    if (!selectedStudent || !messageContent.trim()) return;

    try {
      await apiClient.post("/faculty/messages", {
        student_id: selectedStudent.id,
        content: messageContent,
      });
    } catch (error) {
      console.error("Error sending message:", error);
    }

    // Add to local state
    const newMessage: Message = {
      id: `msg-${Date.now()}`,
      student_id: selectedStudent.id,
      student_name: selectedStudent.name,
      content: messageContent,
      sent_at: new Date().toISOString(),
      is_read: true,
      direction: "sent",
    };

    setMessages([...messages, newMessage]);
    setMessageContent("");
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case "urgent":
        return "bg-red-500";
      case "high":
        return "bg-orange-500";
      case "normal":
        return "bg-blue-500";
      case "low":
        return "bg-gray-500";
      default:
        return "bg-gray-500";
    }
  };

  const getPriorityBg = (priority: string) => {
    switch (priority) {
      case "urgent":
        return "bg-red-500/10 border-red-500/30";
      case "high":
        return "bg-orange-500/10 border-orange-500/30";
      case "normal":
        return "bg-blue-500/10 border-blue-500/30";
      case "low":
        return "bg-gray-500/10 border-gray-500/30";
      default:
        return "bg-gray-500/10 border-gray-500/30";
    }
  };

  const filteredStudents = students.filter(
    (s) =>
      s.name.toLowerCase().includes(studentSearch.toLowerCase()) ||
      s.roll_number.toLowerCase().includes(studentSearch.toLowerCase())
  );

  const studentMessages = selectedStudent
    ? messages.filter((m) => m.student_id === selectedStudent.id)
    : [];

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="h-full text-white p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <MessageSquare className="w-8 h-8 text-blue-500" />
          <div>
            <h1 className="text-2xl font-bold">Communication Center</h1>
            <p className="text-gray-400">Send announcements and messages to students</p>
          </div>
        </div>

        {/* Tab Switcher */}
        <div className="flex bg-gray-800 rounded-lg p-1">
          <button
            onClick={() => setActiveTab("announcements")}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all ${
              activeTab === "announcements" ? "bg-blue-600" : "hover:bg-gray-700"
            }`}
          >
            <Megaphone className="w-4 h-4" />
            Announcements
          </button>
          <button
            onClick={() => setActiveTab("messages")}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all ${
              activeTab === "messages" ? "bg-blue-600" : "hover:bg-gray-700"
            }`}
          >
            <Mail className="w-4 h-4" />
            Messages
          </button>
        </div>
      </div>

      {/* Announcements Tab */}
      {activeTab === "announcements" && (
        <div className="space-y-6">
          {/* Create Button */}
          <div className="flex justify-end">
            <button
              onClick={() => setShowNewAnnouncement(true)}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 rounded-lg hover:bg-blue-700"
            >
              <Plus className="w-4 h-4" />
              New Announcement
            </button>
          </div>

          {/* Announcements List */}
          <div className="space-y-4">
            {announcements.map((announcement) => (
              <div
                key={announcement.id}
                className={`bg-gray-800 rounded-xl p-6 border ${getPriorityBg(announcement.priority)}`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <span className={`px-2 py-0.5 text-xs rounded-full text-white ${getPriorityColor(announcement.priority)}`}>
                        {announcement.priority.toUpperCase()}
                      </span>
                      <span className="text-sm text-gray-400 flex items-center gap-1">
                        <Users className="w-3 h-3" />
                        {announcement.target_name}
                      </span>
                    </div>
                    <h3 className="text-lg font-semibold">{announcement.title}</h3>
                    <p className="text-gray-400 mt-2">{announcement.content}</p>
                    <div className="flex items-center gap-4 mt-4 text-sm text-gray-500">
                      <span className="flex items-center gap-1">
                        <Clock className="w-4 h-4" />
                        {new Date(announcement.created_at).toLocaleDateString()}
                      </span>
                      <span className="flex items-center gap-1">
                        <CheckCircle className="w-4 h-4 text-green-500" />
                        {announcement.read_count}/{announcement.total_recipients} read
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Messages Tab */}
      {activeTab === "messages" && (
        <div className="grid grid-cols-3 gap-6 h-[calc(100vh-200px)]">
          {/* Students List */}
          <div className="bg-gray-800 rounded-xl overflow-hidden flex flex-col">
            <div className="p-4 border-b border-gray-700">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  value={studentSearch}
                  onChange={(e) => setStudentSearch(e.target.value)}
                  placeholder="Search students..."
                  className="w-full bg-gray-700 border border-gray-600 rounded-lg pl-10 pr-4 py-2 text-sm"
                />
              </div>
            </div>

            <div className="flex-1 overflow-y-auto scrollbar-hide">
              {filteredStudents.map((student) => {
                const hasUnread = messages.some(
                  (m) => m.student_id === student.id && m.direction === "received" && !m.is_read
                );
                return (
                  <div
                    key={student.id}
                    onClick={() => setSelectedStudent(student)}
                    className={`p-4 cursor-pointer hover:bg-gray-700 border-b border-gray-700/50 ${
                      selectedStudent?.id === student.id ? "bg-gray-700" : ""
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-gray-600 rounded-full flex items-center justify-center">
                          <User className="w-5 h-5" />
                        </div>
                        <div>
                          <div className="font-medium">{student.name}</div>
                          <div className="text-xs text-gray-400">{student.roll_number}</div>
                        </div>
                      </div>
                      {hasUnread && <span className="w-2 h-2 bg-blue-500 rounded-full"></span>}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Chat Area */}
          <div className="col-span-2 bg-gray-800 rounded-xl overflow-hidden flex flex-col">
            {selectedStudent ? (
              <>
                {/* Chat Header */}
                <div className="p-4 border-b border-gray-700 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-gray-600 rounded-full flex items-center justify-center">
                      <User className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="font-semibold">{selectedStudent.name}</div>
                      <div className="text-xs text-gray-400">
                        {selectedStudent.roll_number} | {selectedStudent.class_name}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Messages */}
                <div className="flex-1 overflow-y-auto scrollbar-hide p-4 space-y-3">
                  {studentMessages.length === 0 ? (
                    <div className="text-center text-gray-500 py-8">
                      <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
                      <p>No messages yet</p>
                      <p className="text-sm">Start a conversation with {selectedStudent.name}</p>
                    </div>
                  ) : (
                    studentMessages.map((message) => (
                      <div
                        key={message.id}
                        className={`flex ${message.direction === "sent" ? "justify-end" : "justify-start"}`}
                      >
                        <div
                          className={`max-w-[70%] p-3 rounded-lg ${
                            message.direction === "sent"
                              ? "bg-blue-600 rounded-br-none"
                              : "bg-gray-700 rounded-bl-none"
                          }`}
                        >
                          <p className="text-sm">{message.content}</p>
                          <div className="text-xs text-gray-300 mt-1 text-right">
                            {new Date(message.sent_at).toLocaleTimeString([], {
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>

                {/* Message Input */}
                <div className="p-4 border-t border-gray-700">
                  <div className="flex gap-3">
                    <input
                      type="text"
                      value={messageContent}
                      onChange={(e) => setMessageContent(e.target.value)}
                      placeholder="Type your message..."
                      className="flex-1 bg-gray-700 border border-gray-600 rounded-lg px-4 py-2"
                      onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                    />
                    <button
                      onClick={sendMessage}
                      disabled={!messageContent.trim()}
                      className="px-4 py-2 bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
                    >
                      <Send className="w-5 h-5" />
                    </button>
                  </div>
                </div>
              </>
            ) : (
              <div className="flex-1 flex items-center justify-center text-gray-500">
                <div className="text-center">
                  <MessageSquare className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>Select a student to start messaging</p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* New Announcement Modal */}
      {showNewAnnouncement && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-xl p-6 w-full max-w-lg">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Create Announcement</h3>
              <button onClick={() => setShowNewAnnouncement(false)} className="text-gray-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-2">Title</label>
                <input
                  type="text"
                  value={announcementForm.title}
                  onChange={(e) => setAnnouncementForm({ ...announcementForm, title: e.target.value })}
                  placeholder="Announcement title"
                  className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2"
                />
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-2">Content</label>
                <textarea
                  value={announcementForm.content}
                  onChange={(e) => setAnnouncementForm({ ...announcementForm, content: e.target.value })}
                  placeholder="Write your announcement..."
                  rows={4}
                  className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 resize-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-2">Priority</label>
                  <select
                    value={announcementForm.priority}
                    onChange={(e) => setAnnouncementForm({ ...announcementForm, priority: e.target.value })}
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2"
                  >
                    <option value="low">Low</option>
                    <option value="normal">Normal</option>
                    <option value="high">High</option>
                    <option value="urgent">Urgent</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm text-gray-400 mb-2">Target</label>
                  <select
                    value={announcementForm.target_type}
                    onChange={(e) => setAnnouncementForm({ ...announcementForm, target_type: e.target.value })}
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2"
                  >
                    <option value="all">All Students</option>
                    <option value="class">Specific Class</option>
                  </select>
                </div>
              </div>

              {announcementForm.target_type === "class" && (
                <div>
                  <label className="block text-sm text-gray-400 mb-2">Select Class</label>
                  <select
                    value={announcementForm.target_id}
                    onChange={(e) => setAnnouncementForm({ ...announcementForm, target_id: e.target.value })}
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2"
                  >
                    <option value="">-- Select Class --</option>
                    {classes.map((cls) => (
                      <option key={cls.id} value={cls.id}>
                        {cls.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowNewAnnouncement(false)}
                className="flex-1 px-4 py-2 bg-gray-700 rounded-lg hover:bg-gray-600"
              >
                Cancel
              </button>
              <button
                onClick={createAnnouncement}
                disabled={!announcementForm.title || !announcementForm.content}
                className="flex-1 px-4 py-2 bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                <div className="flex items-center justify-center gap-2">
                  <Send className="w-4 h-4" />
                  Publish
                </div>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
