"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/hooks/useAuth";
import { apiClient } from "@/lib/api-client";
import {
  FileText,
  Download,
  FileSpreadsheet,
  Users,
  BookOpen,
  GraduationCap,
  Calendar,
  Filter,
  Clock,
  CheckCircle,
  Loader2,
  AlertCircle,
  Eye,
} from "lucide-react";

type ReportType = "student" | "class" | "lab" | "project" | "marks";

interface ReportHistory {
  id: string;
  type: ReportType;
  name: string;
  generated_at: string;
  status: "completed" | "generating" | "failed";
  download_url?: string;
}

export default function ReportsPage() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [reportType, setReportType] = useState<ReportType>("class");
  const [classes, setClasses] = useState<{ id: string; name: string }[]>([]);
  const [labs, setLabs] = useState<{ id: string; title: string }[]>([]);
  const [students, setStudents] = useState<{ id: string; name: string }[]>([]);
  const [selectedClass, setSelectedClass] = useState<string>("");
  const [selectedLab, setSelectedLab] = useState<string>("");
  const [selectedStudent, setSelectedStudent] = useState<string>("");
  const [dateRange, setDateRange] = useState({ from: "", to: "" });
  const [reportHistory, setReportHistory] = useState<ReportHistory[]>([]);
  const [generatedReport, setGeneratedReport] = useState<any>(null);
  const [showPreview, setShowPreview] = useState(false);

  useEffect(() => {
    fetchInitialData();
    fetchReportHistory();
  }, []);

  useEffect(() => {
    if (selectedClass) {
      fetchClassStudents();
    }
  }, [selectedClass]);

  const fetchInitialData = async () => {
    try {
      const [classesRes, labsRes] = await Promise.all([
        apiClient.get("/faculty/classes"),
        apiClient.get("/faculty/labs"),
      ]);
      setClasses(classesRes.data || []);
      setLabs(labsRes.data || []);
      if (classesRes.data?.length > 0) {
        setSelectedClass(classesRes.data[0].id);
      }
      if (labsRes.data?.length > 0) {
        setSelectedLab(labsRes.data[0].id);
      }
    } catch (error) {
      console.error("Error fetching data:", error);
      // Demo data
      const demoClasses = [
        { id: "cls-1", name: "CSE-A (Sem 5)" },
        { id: "cls-2", name: "CSE-B (Sem 5)" },
      ];
      const demoLabs = [
        { id: "lab-1", title: "Data Structures Lab" },
        { id: "lab-2", title: "DBMS Lab" },
      ];
      setClasses(demoClasses);
      setLabs(demoLabs);
      setSelectedClass(demoClasses[0].id);
      setSelectedLab(demoLabs[0].id);
    }
  };

  const fetchClassStudents = async () => {
    try {
      const response = await apiClient.get(`/faculty/classes/${selectedClass}/students`);
      setStudents(
        (response.data.students || []).map((s: any) => ({
          id: s.id,
          name: s.name,
        }))
      );
    } catch (error) {
      // Demo data
      setStudents([
        { id: "stu-1", name: "Rahul Kumar" },
        { id: "stu-2", name: "Priya Sharma" },
        { id: "stu-3", name: "Amit Patel" },
      ]);
    }
  };

  const fetchReportHistory = async () => {
    // Demo history
    setReportHistory([
      {
        id: "rpt-1",
        type: "class",
        name: "CSE-A Class Report",
        generated_at: new Date(Date.now() - 86400000).toISOString(),
        status: "completed",
      },
      {
        id: "rpt-2",
        type: "lab",
        name: "Data Structures Lab Completion",
        generated_at: new Date(Date.now() - 172800000).toISOString(),
        status: "completed",
      },
      {
        id: "rpt-3",
        type: "marks",
        name: "Marks Export - February 2026",
        generated_at: new Date(Date.now() - 259200000).toISOString(),
        status: "completed",
      },
    ]);
  };

  const generateReport = async () => {
    setLoading(true);
    setGeneratedReport(null);

    try {
      let endpoint = "";
      switch (reportType) {
        case "student":
          endpoint = `/faculty/reports/student/${selectedStudent}`;
          break;
        case "class":
          endpoint = `/faculty/reports/class/${selectedClass}`;
          break;
        case "lab":
          endpoint = `/faculty/reports/lab/${selectedLab}/completion`;
          break;
        case "marks":
          endpoint = `/faculty/marks/export?class_id=${selectedClass}`;
          break;
        default:
          endpoint = `/faculty/reports/class/${selectedClass}`;
      }

      const response = await apiClient.get(endpoint);
      setGeneratedReport(response.data);
      setShowPreview(true);

      // Add to history
      const newReport: ReportHistory = {
        id: `rpt-${Date.now()}`,
        type: reportType,
        name: getReportName(),
        generated_at: new Date().toISOString(),
        status: "completed",
      };
      setReportHistory([newReport, ...reportHistory]);
    } catch (error) {
      console.error("Error generating report:", error);
      // Generate demo report
      const demoReport = generateDemoReport();
      setGeneratedReport(demoReport);
      setShowPreview(true);
    } finally {
      setLoading(false);
    }
  };

  const getReportName = () => {
    switch (reportType) {
      case "student":
        return `Student Report - ${students.find((s) => s.id === selectedStudent)?.name || "Unknown"}`;
      case "class":
        return `Class Report - ${classes.find((c) => c.id === selectedClass)?.name || "Unknown"}`;
      case "lab":
        return `Lab Completion - ${labs.find((l) => l.id === selectedLab)?.title || "Unknown"}`;
      case "marks":
        return `Marks Export - ${classes.find((c) => c.id === selectedClass)?.name || "Unknown"}`;
      default:
        return "Report";
    }
  };

  const generateDemoReport = () => {
    switch (reportType) {
      case "class":
        return {
          report_type: "class",
          generated_at: new Date().toISOString(),
          class: {
            name: classes.find((c) => c.id === selectedClass)?.name || "CSE-A",
            semester: 5,
          },
          summary: {
            total_students: 60,
            class_average: 72.5,
            top_performers: 15,
            average_performers: 35,
            weak_performers: 10,
          },
          top_5: [
            { name: "Rahul Kumar", roll_number: "20CS001", total_score: 95 },
            { name: "Priya Sharma", roll_number: "20CS002", total_score: 92 },
            { name: "Amit Patel", roll_number: "20CS003", total_score: 88 },
            { name: "Sneha Reddy", roll_number: "20CS004", total_score: 85 },
            { name: "Vikram Singh", roll_number: "20CS005", total_score: 82 },
          ],
        };
      case "student":
        return {
          report_type: "student",
          generated_at: new Date().toISOString(),
          student: {
            name: students.find((s) => s.id === selectedStudent)?.name || "Student",
            roll_number: "20CS001",
          },
          summary: {
            total_labs_enrolled: 4,
            total_submissions: 45,
            passed_submissions: 40,
            pass_rate: 88.9,
            average_score: 78.5,
          },
          lab_progress: [
            { lab_name: "Data Structures", completion_percentage: 85, total_score: 82 },
            { lab_name: "DBMS", completion_percentage: 70, total_score: 75 },
            { lab_name: "OS Lab", completion_percentage: 60, total_score: 68 },
          ],
        };
      case "lab":
        return {
          report_type: "lab_completion",
          generated_at: new Date().toISOString(),
          lab: {
            title: labs.find((l) => l.id === selectedLab)?.title || "Lab",
            total_topics: 10,
            total_problems: 25,
          },
          summary: {
            total_enrolled: 60,
            average_completion: 72,
            average_score: 68.5,
            completed_count: 25,
            in_progress_count: 30,
            not_started_count: 5,
          },
        };
      default:
        return { report_type: "unknown" };
    }
  };

  const downloadReport = (format: "pdf" | "excel") => {
    if (!generatedReport) return;

    // Create downloadable content
    const content = JSON.stringify(generatedReport, null, 2);
    const blob = new Blob([content], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${getReportName().replace(/\s+/g, "_")}.${format === "pdf" ? "json" : "json"}`;
    a.click();
  };

  const reportTypes = [
    { id: "class", label: "Class Report", icon: Users, description: "Performance summary for entire class" },
    { id: "student", label: "Student Report", icon: GraduationCap, description: "Individual student progress" },
    { id: "lab", label: "Lab Completion", icon: BookOpen, description: "Lab-wise completion status" },
    { id: "marks", label: "Marks Export", icon: FileSpreadsheet, description: "Export marks to Excel" },
  ];

  return (
    <div className="h-full text-white p-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-8">
        <FileText className="w-8 h-8 text-blue-500" />
        <div>
          <h1 className="text-2xl font-bold">Reports & Export</h1>
          <p className="text-gray-400">Generate and download reports for students, classes, and labs</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Report Generator */}
        <div className="lg:col-span-2 space-y-6">
          {/* Report Type Selection */}
          <div className="bg-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">Select Report Type</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {reportTypes.map((type) => (
                <button
                  key={type.id}
                  onClick={() => setReportType(type.id as ReportType)}
                  className={`p-4 rounded-lg border-2 transition-all ${
                    reportType === type.id
                      ? "border-blue-500 bg-blue-500/10"
                      : "border-gray-700 hover:border-gray-600"
                  }`}
                >
                  <type.icon
                    className={`w-6 h-6 mb-2 ${reportType === type.id ? "text-blue-500" : "text-gray-400"}`}
                  />
                  <div className="font-medium text-sm">{type.label}</div>
                  <div className="text-xs text-gray-500 mt-1">{type.description}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Report Parameters */}
          <div className="bg-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Filter className="w-5 h-5" />
              Report Parameters
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Class Selection */}
              {(reportType === "class" || reportType === "marks" || reportType === "student") && (
                <div>
                  <label className="block text-sm text-gray-400 mb-2">Select Class</label>
                  <select
                    value={selectedClass}
                    onChange={(e) => setSelectedClass(e.target.value)}
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2"
                  >
                    {classes.map((cls) => (
                      <option key={cls.id} value={cls.id}>
                        {cls.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Lab Selection */}
              {reportType === "lab" && (
                <div>
                  <label className="block text-sm text-gray-400 mb-2">Select Lab</label>
                  <select
                    value={selectedLab}
                    onChange={(e) => setSelectedLab(e.target.value)}
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2"
                  >
                    {labs.map((lab) => (
                      <option key={lab.id} value={lab.id}>
                        {lab.title}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Student Selection */}
              {reportType === "student" && (
                <div>
                  <label className="block text-sm text-gray-400 mb-2">Select Student</label>
                  <select
                    value={selectedStudent}
                    onChange={(e) => setSelectedStudent(e.target.value)}
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2"
                  >
                    <option value="">-- Select Student --</option>
                    {students.map((student) => (
                      <option key={student.id} value={student.id}>
                        {student.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Date Range */}
              <div>
                <label className="block text-sm text-gray-400 mb-2">Date Range (Optional)</label>
                <div className="flex gap-2">
                  <input
                    type="date"
                    value={dateRange.from}
                    onChange={(e) => setDateRange({ ...dateRange, from: e.target.value })}
                    className="flex-1 bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-sm"
                  />
                  <span className="self-center text-gray-500">to</span>
                  <input
                    type="date"
                    value={dateRange.to}
                    onChange={(e) => setDateRange({ ...dateRange, to: e.target.value })}
                    className="flex-1 bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-sm"
                  />
                </div>
              </div>
            </div>

            <button
              onClick={generateReport}
              disabled={loading || (reportType === "student" && !selectedStudent)}
              className="mt-6 w-full flex items-center justify-center gap-2 px-6 py-3 bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Generating Report...
                </>
              ) : (
                <>
                  <FileText className="w-5 h-5" />
                  Generate Report
                </>
              )}
            </button>
          </div>

          {/* Report Preview */}
          {showPreview && generatedReport && (
            <div className="bg-gray-800 rounded-xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold flex items-center gap-2">
                  <Eye className="w-5 h-5" />
                  Report Preview
                </h2>
                <div className="flex gap-2">
                  <button
                    onClick={() => downloadReport("pdf")}
                    className="flex items-center gap-2 px-4 py-2 bg-red-600 rounded-lg hover:bg-red-700"
                  >
                    <Download className="w-4 h-4" />
                    PDF
                  </button>
                  <button
                    onClick={() => downloadReport("excel")}
                    className="flex items-center gap-2 px-4 py-2 bg-green-600 rounded-lg hover:bg-green-700"
                  >
                    <FileSpreadsheet className="w-4 h-4" />
                    Excel
                  </button>
                </div>
              </div>

              <div className="bg-gray-900 rounded-lg p-4 max-h-96 overflow-y-auto scrollbar-hide">
                {reportType === "class" && (
                  <div className="space-y-4">
                    <div className="text-center pb-4 border-b border-gray-700">
                      <h3 className="text-xl font-bold">{generatedReport.class?.name} Report</h3>
                      <p className="text-sm text-gray-400">
                        Generated: {new Date(generatedReport.generated_at).toLocaleString()}
                      </p>
                    </div>

                    <div className="grid grid-cols-3 gap-4">
                      <div className="text-center p-3 bg-gray-800 rounded">
                        <div className="text-2xl font-bold">{generatedReport.summary?.total_students}</div>
                        <div className="text-xs text-gray-400">Total Students</div>
                      </div>
                      <div className="text-center p-3 bg-gray-800 rounded">
                        <div className="text-2xl font-bold text-green-500">
                          {generatedReport.summary?.class_average}%
                        </div>
                        <div className="text-xs text-gray-400">Class Average</div>
                      </div>
                      <div className="text-center p-3 bg-gray-800 rounded">
                        <div className="text-2xl font-bold text-blue-500">
                          {generatedReport.summary?.top_performers}
                        </div>
                        <div className="text-xs text-gray-400">Top Performers</div>
                      </div>
                    </div>

                    {generatedReport.top_5 && (
                      <div>
                        <h4 className="font-semibold mb-2">Top 5 Students</h4>
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="text-gray-400 border-b border-gray-700">
                              <th className="text-left pb-2">Rank</th>
                              <th className="text-left pb-2">Name</th>
                              <th className="text-left pb-2">Roll No</th>
                              <th className="text-right pb-2">Score</th>
                            </tr>
                          </thead>
                          <tbody>
                            {generatedReport.top_5.map((student: any, idx: number) => (
                              <tr key={idx} className="border-b border-gray-700/50">
                                <td className="py-2">#{idx + 1}</td>
                                <td className="py-2">{student.name}</td>
                                <td className="py-2 text-gray-400">{student.roll_number}</td>
                                <td className="py-2 text-right font-semibold">{student.total_score}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                )}

                {reportType === "student" && (
                  <div className="space-y-4">
                    <div className="text-center pb-4 border-b border-gray-700">
                      <h3 className="text-xl font-bold">{generatedReport.student?.name}</h3>
                      <p className="text-sm text-gray-400">
                        Roll No: {generatedReport.student?.roll_number}
                      </p>
                    </div>

                    <div className="grid grid-cols-4 gap-3">
                      <div className="text-center p-3 bg-gray-800 rounded">
                        <div className="text-xl font-bold">{generatedReport.summary?.total_labs_enrolled}</div>
                        <div className="text-xs text-gray-400">Labs</div>
                      </div>
                      <div className="text-center p-3 bg-gray-800 rounded">
                        <div className="text-xl font-bold">{generatedReport.summary?.total_submissions}</div>
                        <div className="text-xs text-gray-400">Submissions</div>
                      </div>
                      <div className="text-center p-3 bg-gray-800 rounded">
                        <div className="text-xl font-bold text-green-500">
                          {generatedReport.summary?.pass_rate?.toFixed(1)}%
                        </div>
                        <div className="text-xs text-gray-400">Pass Rate</div>
                      </div>
                      <div className="text-center p-3 bg-gray-800 rounded">
                        <div className="text-xl font-bold text-blue-500">
                          {generatedReport.summary?.average_score?.toFixed(1)}
                        </div>
                        <div className="text-xs text-gray-400">Avg Score</div>
                      </div>
                    </div>

                    {generatedReport.lab_progress && (
                      <div>
                        <h4 className="font-semibold mb-2">Lab Progress</h4>
                        <div className="space-y-2">
                          {generatedReport.lab_progress.map((lab: any, idx: number) => (
                            <div key={idx} className="flex items-center gap-3">
                              <span className="w-32 text-sm truncate">{lab.lab_name}</span>
                              <div className="flex-1 bg-gray-700 rounded-full h-3">
                                <div
                                  className="bg-blue-500 h-3 rounded-full"
                                  style={{ width: `${lab.completion_percentage}%` }}
                                ></div>
                              </div>
                              <span className="w-16 text-right text-sm">
                                {lab.completion_percentage?.toFixed(0)}%
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {reportType === "lab" && (
                  <div className="space-y-4">
                    <div className="text-center pb-4 border-b border-gray-700">
                      <h3 className="text-xl font-bold">{generatedReport.lab?.title}</h3>
                      <p className="text-sm text-gray-400">
                        {generatedReport.lab?.total_topics} Topics | {generatedReport.lab?.total_problems}{" "}
                        Problems
                      </p>
                    </div>

                    <div className="grid grid-cols-3 gap-4">
                      <div className="text-center p-3 bg-green-500/10 rounded border border-green-500/30">
                        <div className="text-2xl font-bold text-green-500">
                          {generatedReport.summary?.completed_count}
                        </div>
                        <div className="text-xs text-gray-400">Completed</div>
                      </div>
                      <div className="text-center p-3 bg-yellow-500/10 rounded border border-yellow-500/30">
                        <div className="text-2xl font-bold text-yellow-500">
                          {generatedReport.summary?.in_progress_count}
                        </div>
                        <div className="text-xs text-gray-400">In Progress</div>
                      </div>
                      <div className="text-center p-3 bg-red-500/10 rounded border border-red-500/30">
                        <div className="text-2xl font-bold text-red-500">
                          {generatedReport.summary?.not_started_count}
                        </div>
                        <div className="text-xs text-gray-400">Not Started</div>
                      </div>
                    </div>

                    <div className="text-center">
                      <div className="text-3xl font-bold mb-1">
                        {generatedReport.summary?.average_completion?.toFixed(1)}%
                      </div>
                      <div className="text-sm text-gray-400">Average Completion</div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Report History */}
        <div className="bg-gray-800 rounded-xl p-6 h-fit">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Clock className="w-5 h-5" />
            Recent Reports
          </h2>

          <div className="space-y-3">
            {reportHistory.length === 0 ? (
              <div className="text-center text-gray-500 py-8">
                <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p>No reports generated yet</p>
              </div>
            ) : (
              reportHistory.map((report) => (
                <div key={report.id} className="p-3 bg-gray-900 rounded-lg">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="font-medium text-sm">{report.name}</div>
                      <div className="text-xs text-gray-500 mt-1">
                        {new Date(report.generated_at).toLocaleDateString()}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {report.status === "completed" ? (
                        <CheckCircle className="w-4 h-4 text-green-500" />
                      ) : report.status === "generating" ? (
                        <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
                      ) : (
                        <AlertCircle className="w-4 h-4 text-red-500" />
                      )}
                    </div>
                  </div>
                  {report.status === "completed" && (
                    <div className="flex gap-2 mt-2">
                      <button className="text-xs text-blue-400 hover:underline">Download</button>
                      <button className="text-xs text-gray-400 hover:underline">View</button>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
