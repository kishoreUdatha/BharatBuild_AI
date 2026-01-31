"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/hooks/useAuth";
import { apiClient } from "@/lib/api-client";
import {
  ShieldAlert,
  Bot,
  Copy,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Settings,
  RefreshCw,
  Eye,
  Filter,
  Download,
  ChevronDown,
  ChevronUp,
  TrendingUp,
  TrendingDown,
} from "lucide-react";

interface SubmissionAnalysis {
  id: string;
  student_id: string;
  student_name: string;
  problem_title: string;
  lab_title: string;
  ai_score: number;
  plagiarism_score: number;
  submitted_at: string;
  status: string;
  risk_level: "low" | "medium" | "high";
}

interface ClassIntegritySummary {
  class_id: string;
  class_name: string;
  total_submissions: number;
  avg_ai_score: number;
  avg_plagiarism_score: number;
  high_risk_count: number;
  medium_risk_count: number;
  low_risk_count: number;
}

interface IntegrityThresholds {
  ai_warning: number;
  ai_critical: number;
  plagiarism_warning: number;
  plagiarism_critical: number;
}

export default function IntegrityDashboard() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [classes, setClasses] = useState<{ id: string; name: string }[]>([]);
  const [selectedClass, setSelectedClass] = useState<string>("");
  const [submissions, setSubmissions] = useState<SubmissionAnalysis[]>([]);
  const [summary, setSummary] = useState<ClassIntegritySummary | null>(null);
  const [thresholds, setThresholds] = useState<IntegrityThresholds>({
    ai_warning: 30,
    ai_critical: 60,
    plagiarism_warning: 20,
    plagiarism_critical: 50,
  });
  const [showSettings, setShowSettings] = useState(false);
  const [filter, setFilter] = useState<"all" | "high" | "medium" | "low">("all");
  const [sortBy, setSortBy] = useState<"ai" | "plagiarism" | "date">("date");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");

  useEffect(() => {
    fetchClasses();
  }, []);

  useEffect(() => {
    if (selectedClass) {
      fetchIntegrityData();
    }
  }, [selectedClass]);

  const fetchClasses = async () => {
    try {
      const response = await apiClient.get("/faculty/classes");
      setClasses(response.data || []);
      if (response.data?.length > 0) {
        setSelectedClass(response.data[0].id);
      }
    } catch (error) {
      console.error("Error fetching classes:", error);
      // Demo data
      const demoClasses = [
        { id: "cls-1", name: "CSE-A (Sem 5)" },
        { id: "cls-2", name: "CSE-B (Sem 5)" },
        { id: "cls-3", name: "CSE-A (Sem 3)" },
      ];
      setClasses(demoClasses);
      setSelectedClass(demoClasses[0].id);
    } finally {
      setLoading(false);
    }
  };

  const fetchIntegrityData = async () => {
    setLoading(true);
    try {
      const [submissionsRes, summaryRes] = await Promise.all([
        apiClient.get(`/faculty/class/${selectedClass}/submissions-analysis`),
        apiClient.get(`/faculty/class/${selectedClass}/integrity-report`),
      ]);
      setSubmissions(submissionsRes.data || []);
      setSummary(summaryRes.data || null);
    } catch (error) {
      console.error("Error fetching integrity data:", error);
      // Demo data
      const demoSubmissions: SubmissionAnalysis[] = [
        {
          id: "sub-1",
          student_id: "stu-1",
          student_name: "Rahul Kumar",
          problem_title: "Binary Search Tree",
          lab_title: "Data Structures Lab",
          ai_score: 72,
          plagiarism_score: 15,
          submitted_at: new Date().toISOString(),
          status: "accepted",
          risk_level: "high",
        },
        {
          id: "sub-2",
          student_id: "stu-2",
          student_name: "Priya Sharma",
          problem_title: "Quick Sort",
          lab_title: "Data Structures Lab",
          ai_score: 45,
          plagiarism_score: 8,
          submitted_at: new Date(Date.now() - 86400000).toISOString(),
          status: "accepted",
          risk_level: "medium",
        },
        {
          id: "sub-3",
          student_id: "stu-3",
          student_name: "Amit Patel",
          problem_title: "Linked List",
          lab_title: "Data Structures Lab",
          ai_score: 12,
          plagiarism_score: 5,
          submitted_at: new Date(Date.now() - 172800000).toISOString(),
          status: "accepted",
          risk_level: "low",
        },
        {
          id: "sub-4",
          student_id: "stu-4",
          student_name: "Sneha Reddy",
          problem_title: "Graph BFS",
          lab_title: "Data Structures Lab",
          ai_score: 65,
          plagiarism_score: 55,
          submitted_at: new Date(Date.now() - 259200000).toISOString(),
          status: "accepted",
          risk_level: "high",
        },
        {
          id: "sub-5",
          student_id: "stu-5",
          student_name: "Vikram Singh",
          problem_title: "Binary Search Tree",
          lab_title: "Data Structures Lab",
          ai_score: 28,
          plagiarism_score: 12,
          submitted_at: new Date(Date.now() - 345600000).toISOString(),
          status: "accepted",
          risk_level: "low",
        },
      ];

      const demoSummary: ClassIntegritySummary = {
        class_id: selectedClass,
        class_name: classes.find((c) => c.id === selectedClass)?.name || "Class",
        total_submissions: 48,
        avg_ai_score: 35,
        avg_plagiarism_score: 18,
        high_risk_count: 5,
        medium_risk_count: 12,
        low_risk_count: 31,
      };

      setSubmissions(demoSubmissions);
      setSummary(demoSummary);
    } finally {
      setLoading(false);
    }
  };

  const getRiskLevel = (aiScore: number, plagScore: number): "low" | "medium" | "high" => {
    if (aiScore >= thresholds.ai_critical || plagScore >= thresholds.plagiarism_critical) {
      return "high";
    }
    if (aiScore >= thresholds.ai_warning || plagScore >= thresholds.plagiarism_warning) {
      return "medium";
    }
    return "low";
  };

  const getRiskColor = (level: "low" | "medium" | "high") => {
    switch (level) {
      case "high":
        return "text-red-500 bg-red-500/10";
      case "medium":
        return "text-yellow-500 bg-yellow-500/10";
      case "low":
        return "text-green-500 bg-green-500/10";
    }
  };

  const getRiskIcon = (level: "low" | "medium" | "high") => {
    switch (level) {
      case "high":
        return <XCircle className="w-4 h-4" />;
      case "medium":
        return <AlertTriangle className="w-4 h-4" />;
      case "low":
        return <CheckCircle className="w-4 h-4" />;
    }
  };

  const getScoreColor = (score: number, type: "ai" | "plagiarism") => {
    const warning = type === "ai" ? thresholds.ai_warning : thresholds.plagiarism_warning;
    const critical = type === "ai" ? thresholds.ai_critical : thresholds.plagiarism_critical;

    if (score >= critical) return "text-red-500";
    if (score >= warning) return "text-yellow-500";
    return "text-green-500";
  };

  const filteredSubmissions = submissions
    .filter((sub) => filter === "all" || sub.risk_level === filter)
    .sort((a, b) => {
      let comparison = 0;
      switch (sortBy) {
        case "ai":
          comparison = a.ai_score - b.ai_score;
          break;
        case "plagiarism":
          comparison = a.plagiarism_score - b.plagiarism_score;
          break;
        case "date":
          comparison = new Date(a.submitted_at).getTime() - new Date(b.submitted_at).getTime();
          break;
      }
      return sortOrder === "asc" ? comparison : -comparison;
    });

  const saveThresholds = async () => {
    try {
      await apiClient.put("/faculty/settings/thresholds", thresholds);
      setShowSettings(false);
    } catch (error) {
      console.error("Error saving thresholds:", error);
      setShowSettings(false);
    }
  };

  const exportReport = () => {
    // Export to CSV
    const headers = ["Student", "Problem", "Lab", "AI Score", "Plagiarism Score", "Risk Level", "Date"];
    const rows = filteredSubmissions.map((sub) => [
      sub.student_name,
      sub.problem_title,
      sub.lab_title,
      sub.ai_score.toString(),
      sub.plagiarism_score.toString(),
      sub.risk_level,
      new Date(sub.submitted_at).toLocaleDateString(),
    ]);

    const csv = [headers, ...rows].map((row) => row.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `integrity-report-${selectedClass}.csv`;
    a.click();
  };

  if (loading && !summary) {
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
          <ShieldAlert className="w-8 h-8 text-blue-500" />
          <div>
            <h1 className="text-2xl font-bold">Academic Integrity Dashboard</h1>
            <p className="text-gray-400">Monitor AI usage and plagiarism in submissions</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={selectedClass}
            onChange={(e) => setSelectedClass(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-lg px-4 py-2"
          >
            {classes.map((cls) => (
              <option key={cls.id} value={cls.id}>
                {cls.name}
              </option>
            ))}
          </select>
          <button
            onClick={() => setShowSettings(true)}
            className="p-2 bg-gray-800 rounded-lg hover:bg-gray-700"
          >
            <Settings className="w-5 h-5" />
          </button>
          <button
            onClick={fetchIntegrityData}
            className="p-2 bg-gray-800 rounded-lg hover:bg-gray-700"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-gray-800 rounded-xl p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-gray-400">Total Submissions</span>
              <span className="text-2xl font-bold">{summary.total_submissions}</span>
            </div>
            <div className="text-sm text-gray-500">Analyzed in selected class</div>
          </div>

          <div className="bg-gray-800 rounded-xl p-6">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Bot className="w-5 h-5 text-purple-500" />
                <span className="text-gray-400">Avg AI Score</span>
              </div>
              <span className={`text-2xl font-bold ${getScoreColor(summary.avg_ai_score, "ai")}`}>
                {summary.avg_ai_score}%
              </span>
            </div>
            <div className="flex items-center gap-1 text-sm">
              {summary.avg_ai_score > 30 ? (
                <>
                  <TrendingUp className="w-4 h-4 text-red-500" />
                  <span className="text-red-500">Above threshold</span>
                </>
              ) : (
                <>
                  <TrendingDown className="w-4 h-4 text-green-500" />
                  <span className="text-green-500">Within limits</span>
                </>
              )}
            </div>
          </div>

          <div className="bg-gray-800 rounded-xl p-6">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Copy className="w-5 h-5 text-orange-500" />
                <span className="text-gray-400">Avg Plagiarism</span>
              </div>
              <span
                className={`text-2xl font-bold ${getScoreColor(summary.avg_plagiarism_score, "plagiarism")}`}
              >
                {summary.avg_plagiarism_score}%
              </span>
            </div>
            <div className="flex items-center gap-1 text-sm">
              {summary.avg_plagiarism_score > 20 ? (
                <>
                  <TrendingUp className="w-4 h-4 text-red-500" />
                  <span className="text-red-500">Above threshold</span>
                </>
              ) : (
                <>
                  <TrendingDown className="w-4 h-4 text-green-500" />
                  <span className="text-green-500">Within limits</span>
                </>
              )}
            </div>
          </div>

          <div className="bg-gray-800 rounded-xl p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-gray-400">Risk Distribution</span>
              <AlertTriangle className="w-5 h-5 text-yellow-500" />
            </div>
            <div className="flex items-center gap-4 text-sm">
              <div className="flex items-center gap-1">
                <span className="w-3 h-3 rounded-full bg-red-500"></span>
                <span>{summary.high_risk_count} High</span>
              </div>
              <div className="flex items-center gap-1">
                <span className="w-3 h-3 rounded-full bg-yellow-500"></span>
                <span>{summary.medium_risk_count} Med</span>
              </div>
              <div className="flex items-center gap-1">
                <span className="w-3 h-3 rounded-full bg-green-500"></span>
                <span>{summary.low_risk_count} Low</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Risk Distribution Chart */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        {/* AI Score Distribution */}
        <div className="bg-gray-800 rounded-xl p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Bot className="w-5 h-5 text-purple-500" />
            AI Detection Distribution
          </h3>
          <div className="space-y-3">
            {["0-30% (Low)", "30-60% (Medium)", "60-100% (High)"].map((range, idx) => {
              const counts = [
                submissions.filter((s) => s.ai_score < 30).length,
                submissions.filter((s) => s.ai_score >= 30 && s.ai_score < 60).length,
                submissions.filter((s) => s.ai_score >= 60).length,
              ];
              const total = submissions.length || 1;
              const percentage = (counts[idx] / total) * 100;
              const colors = ["bg-green-500", "bg-yellow-500", "bg-red-500"];

              return (
                <div key={range}>
                  <div className="flex justify-between text-sm mb-1">
                    <span>{range}</span>
                    <span>
                      {counts[idx]} ({percentage.toFixed(0)}%)
                    </span>
                  </div>
                  <div className="w-full bg-gray-700 rounded-full h-3">
                    <div
                      className={`${colors[idx]} h-3 rounded-full transition-all duration-500`}
                      style={{ width: `${percentage}%` }}
                    ></div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Plagiarism Distribution */}
        <div className="bg-gray-800 rounded-xl p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Copy className="w-5 h-5 text-orange-500" />
            Plagiarism Distribution
          </h3>
          <div className="space-y-3">
            {["0-20% (Low)", "20-50% (Medium)", "50-100% (High)"].map((range, idx) => {
              const counts = [
                submissions.filter((s) => s.plagiarism_score < 20).length,
                submissions.filter((s) => s.plagiarism_score >= 20 && s.plagiarism_score < 50).length,
                submissions.filter((s) => s.plagiarism_score >= 50).length,
              ];
              const total = submissions.length || 1;
              const percentage = (counts[idx] / total) * 100;
              const colors = ["bg-green-500", "bg-yellow-500", "bg-red-500"];

              return (
                <div key={range}>
                  <div className="flex justify-between text-sm mb-1">
                    <span>{range}</span>
                    <span>
                      {counts[idx]} ({percentage.toFixed(0)}%)
                    </span>
                  </div>
                  <div className="w-full bg-gray-700 rounded-full h-3">
                    <div
                      className={`${colors[idx]} h-3 rounded-full transition-all duration-500`}
                      style={{ width: `${percentage}%` }}
                    ></div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Submissions Table */}
      <div className="bg-gray-800 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Submission Analysis</h3>
          <div className="flex items-center gap-3">
            {/* Filter */}
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-gray-400" />
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value as typeof filter)}
                className="bg-gray-700 border border-gray-600 rounded px-3 py-1.5 text-sm"
              >
                <option value="all">All Risks</option>
                <option value="high">High Risk</option>
                <option value="medium">Medium Risk</option>
                <option value="low">Low Risk</option>
              </select>
            </div>

            {/* Sort */}
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
              className="bg-gray-700 border border-gray-600 rounded px-3 py-1.5 text-sm"
            >
              <option value="date">Sort by Date</option>
              <option value="ai">Sort by AI Score</option>
              <option value="plagiarism">Sort by Plagiarism</option>
            </select>

            <button
              onClick={() => setSortOrder(sortOrder === "asc" ? "desc" : "asc")}
              className="p-1.5 bg-gray-700 rounded"
            >
              {sortOrder === "asc" ? (
                <ChevronUp className="w-4 h-4" />
              ) : (
                <ChevronDown className="w-4 h-4" />
              )}
            </button>

            <button
              onClick={exportReport}
              className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 rounded text-sm hover:bg-blue-700"
            >
              <Download className="w-4 h-4" />
              Export
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-gray-400 border-b border-gray-700">
                <th className="pb-3 font-medium">Student</th>
                <th className="pb-3 font-medium">Problem</th>
                <th className="pb-3 font-medium">Lab</th>
                <th className="pb-3 font-medium text-center">AI Score</th>
                <th className="pb-3 font-medium text-center">Plagiarism</th>
                <th className="pb-3 font-medium text-center">Risk</th>
                <th className="pb-3 font-medium">Date</th>
                <th className="pb-3 font-medium text-center">Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredSubmissions.map((sub) => (
                <tr key={sub.id} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                  <td className="py-3">
                    <div className="font-medium">{sub.student_name}</div>
                  </td>
                  <td className="py-3 text-gray-400">{sub.problem_title}</td>
                  <td className="py-3 text-gray-400">{sub.lab_title}</td>
                  <td className="py-3 text-center">
                    <span className={`font-semibold ${getScoreColor(sub.ai_score, "ai")}`}>
                      {sub.ai_score}%
                    </span>
                  </td>
                  <td className="py-3 text-center">
                    <span className={`font-semibold ${getScoreColor(sub.plagiarism_score, "plagiarism")}`}>
                      {sub.plagiarism_score}%
                    </span>
                  </td>
                  <td className="py-3 text-center">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${getRiskColor(sub.risk_level)}`}
                    >
                      {getRiskIcon(sub.risk_level)}
                      {sub.risk_level.toUpperCase()}
                    </span>
                  </td>
                  <td className="py-3 text-gray-400 text-sm">
                    {new Date(sub.submitted_at).toLocaleDateString()}
                  </td>
                  <td className="py-3 text-center">
                    <a
                      href={`/faculty/code-review?submission=${sub.id}`}
                      className="inline-flex items-center gap-1 px-3 py-1 bg-blue-600/20 text-blue-400 rounded hover:bg-blue-600/30"
                    >
                      <Eye className="w-4 h-4" />
                      Review
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {filteredSubmissions.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              No submissions found matching the filter criteria.
            </div>
          )}
        </div>
      </div>

      {/* Settings Modal */}
      {showSettings && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-xl p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold mb-4">Configure Thresholds</h3>

            <div className="space-y-6">
              {/* AI Thresholds */}
              <div>
                <h4 className="text-sm font-medium text-purple-400 mb-3 flex items-center gap-2">
                  <Bot className="w-4 h-4" />
                  AI Detection Thresholds
                </h4>
                <div className="space-y-3">
                  <div>
                    <label className="text-sm text-gray-400">Warning Level (%)</label>
                    <input
                      type="range"
                      min="10"
                      max="80"
                      value={thresholds.ai_warning}
                      onChange={(e) =>
                        setThresholds({ ...thresholds, ai_warning: parseInt(e.target.value) })
                      }
                      className="w-full"
                    />
                    <div className="flex justify-between text-xs text-gray-500">
                      <span>10%</span>
                      <span className="text-yellow-500">{thresholds.ai_warning}%</span>
                      <span>80%</span>
                    </div>
                  </div>
                  <div>
                    <label className="text-sm text-gray-400">Critical Level (%)</label>
                    <input
                      type="range"
                      min="30"
                      max="100"
                      value={thresholds.ai_critical}
                      onChange={(e) =>
                        setThresholds({ ...thresholds, ai_critical: parseInt(e.target.value) })
                      }
                      className="w-full"
                    />
                    <div className="flex justify-between text-xs text-gray-500">
                      <span>30%</span>
                      <span className="text-red-500">{thresholds.ai_critical}%</span>
                      <span>100%</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Plagiarism Thresholds */}
              <div>
                <h4 className="text-sm font-medium text-orange-400 mb-3 flex items-center gap-2">
                  <Copy className="w-4 h-4" />
                  Plagiarism Thresholds
                </h4>
                <div className="space-y-3">
                  <div>
                    <label className="text-sm text-gray-400">Warning Level (%)</label>
                    <input
                      type="range"
                      min="5"
                      max="60"
                      value={thresholds.plagiarism_warning}
                      onChange={(e) =>
                        setThresholds({ ...thresholds, plagiarism_warning: parseInt(e.target.value) })
                      }
                      className="w-full"
                    />
                    <div className="flex justify-between text-xs text-gray-500">
                      <span>5%</span>
                      <span className="text-yellow-500">{thresholds.plagiarism_warning}%</span>
                      <span>60%</span>
                    </div>
                  </div>
                  <div>
                    <label className="text-sm text-gray-400">Critical Level (%)</label>
                    <input
                      type="range"
                      min="20"
                      max="100"
                      value={thresholds.plagiarism_critical}
                      onChange={(e) =>
                        setThresholds({ ...thresholds, plagiarism_critical: parseInt(e.target.value) })
                      }
                      className="w-full"
                    />
                    <div className="flex justify-between text-xs text-gray-500">
                      <span>20%</span>
                      <span className="text-red-500">{thresholds.plagiarism_critical}%</span>
                      <span>100%</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowSettings(false)}
                className="flex-1 px-4 py-2 bg-gray-700 rounded-lg hover:bg-gray-600"
              >
                Cancel
              </button>
              <button
                onClick={saveThresholds}
                className="flex-1 px-4 py-2 bg-blue-600 rounded-lg hover:bg-blue-700"
              >
                Save Thresholds
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
