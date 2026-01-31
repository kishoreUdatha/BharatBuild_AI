"use client";

import { useState, useEffect, useRef, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { apiClient } from "@/lib/api-client";
import dynamic from "next/dynamic";
import {
  Code,
  MessageSquare,
  CheckCircle,
  XCircle,
  Download,
  ChevronLeft,
  ChevronRight,
  Clock,
  User,
  FileCode,
  GitCompare,
  Send,
  Trash2,
  Bot,
  Copy,
  AlertTriangle,
  Play,
  Eye,
} from "lucide-react";

// Dynamic import for Monaco Editor
const MonacoEditor = dynamic(() => import("@monaco-editor/react"), {
  ssr: false,
  loading: () => (
    <div className="h-full flex items-center justify-center bg-gray-900">
      <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500"></div>
    </div>
  ),
});

interface Submission {
  id: string;
  student_id: string;
  student_name: string;
  problem_id: string;
  problem_title: string;
  lab_title: string;
  language: string;
  code: string;
  status: string;
  score: number;
  tests_passed: number;
  tests_total: number;
  execution_time_ms: number;
  ai_score: number;
  plagiarism_score: number;
  submitted_at: string;
  review_status: "pending" | "approved" | "rejected" | "needs_revision";
}

interface CodeComment {
  id: string;
  line_number: number;
  content: string;
  author: string;
  created_at: string;
}

interface SubmissionVersion {
  id: string;
  version: number;
  code: string;
  submitted_at: string;
  tests_passed: number;
  tests_total: number;
}

function CodeReviewContent() {
  const searchParams = useSearchParams();
  const submissionId = searchParams.get("submission");
  const { user } = useAuth();

  const [loading, setLoading] = useState(true);
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [selectedSubmission, setSelectedSubmission] = useState<Submission | null>(null);
  const [comments, setComments] = useState<CodeComment[]>([]);
  const [versions, setVersions] = useState<SubmissionVersion[]>([]);
  const [newComment, setNewComment] = useState("");
  const [selectedLine, setSelectedLine] = useState<number | null>(null);
  const [showDiff, setShowDiff] = useState(false);
  const [diffVersion, setDiffVersion] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [filterStatus, setFilterStatus] = useState<string>("all");

  const editorRef = useRef<any>(null);

  useEffect(() => {
    fetchSubmissions();
  }, []);

  useEffect(() => {
    if (submissionId && submissions.length > 0) {
      const sub = submissions.find((s) => s.id === submissionId);
      if (sub) {
        setSelectedSubmission(sub);
        fetchSubmissionDetails(sub.id);
      }
    }
  }, [submissionId, submissions]);

  const fetchSubmissions = async () => {
    try {
      const response = await apiClient.get("/faculty/submissions/pending-review");
      setSubmissions(response.data || []);
    } catch (error) {
      console.error("Error fetching submissions:", error);
      // Demo data
      const demoSubmissions: Submission[] = [
        {
          id: "sub-1",
          student_id: "stu-1",
          student_name: "Rahul Kumar",
          problem_id: "prob-1",
          problem_title: "Binary Search Tree Implementation",
          lab_title: "Data Structures Lab",
          language: "python",
          code: `class Node:
    def __init__(self, value):
        self.value = value
        self.left = None
        self.right = None

class BinarySearchTree:
    def __init__(self):
        self.root = None

    def insert(self, value):
        if not self.root:
            self.root = Node(value)
        else:
            self._insert_recursive(self.root, value)

    def _insert_recursive(self, node, value):
        if value < node.value:
            if node.left is None:
                node.left = Node(value)
            else:
                self._insert_recursive(node.left, value)
        else:
            if node.right is None:
                node.right = Node(value)
            else:
                self._insert_recursive(node.right, value)

    def search(self, value):
        return self._search_recursive(self.root, value)

    def _search_recursive(self, node, value):
        if node is None or node.value == value:
            return node
        if value < node.value:
            return self._search_recursive(node.left, value)
        return self._search_recursive(node.right, value)

    def inorder(self):
        result = []
        self._inorder_recursive(self.root, result)
        return result

    def _inorder_recursive(self, node, result):
        if node:
            self._inorder_recursive(node.left, result)
            result.append(node.value)
            self._inorder_recursive(node.right, result)

# Test
bst = BinarySearchTree()
for val in [5, 3, 7, 1, 4, 6, 8]:
    bst.insert(val)
print(bst.inorder())  # [1, 3, 4, 5, 6, 7, 8]`,
          status: "accepted",
          score: 85,
          tests_passed: 8,
          tests_total: 10,
          execution_time_ms: 45,
          ai_score: 72,
          plagiarism_score: 15,
          submitted_at: new Date().toISOString(),
          review_status: "pending",
        },
        {
          id: "sub-2",
          student_id: "stu-2",
          student_name: "Priya Sharma",
          problem_id: "prob-2",
          problem_title: "Quick Sort Algorithm",
          lab_title: "Data Structures Lab",
          language: "python",
          code: `def quicksort(arr):
    if len(arr) <= 1:
        return arr

    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]

    return quicksort(left) + middle + quicksort(right)

# Test
arr = [64, 34, 25, 12, 22, 11, 90]
print(quicksort(arr))`,
          status: "accepted",
          score: 100,
          tests_passed: 10,
          tests_total: 10,
          execution_time_ms: 32,
          ai_score: 25,
          plagiarism_score: 8,
          submitted_at: new Date(Date.now() - 86400000).toISOString(),
          review_status: "pending",
        },
        {
          id: "sub-3",
          student_id: "stu-3",
          student_name: "Amit Patel",
          problem_id: "prob-3",
          problem_title: "Linked List Operations",
          lab_title: "Data Structures Lab",
          language: "c",
          code: `#include <stdio.h>
#include <stdlib.h>

struct Node {
    int data;
    struct Node* next;
};

void push(struct Node** head_ref, int new_data) {
    struct Node* new_node = (struct Node*)malloc(sizeof(struct Node));
    new_node->data = new_data;
    new_node->next = (*head_ref);
    (*head_ref) = new_node;
}

void printList(struct Node* node) {
    while (node != NULL) {
        printf("%d -> ", node->data);
        node = node->next;
    }
    printf("NULL\\n");
}

int main() {
    struct Node* head = NULL;
    push(&head, 7);
    push(&head, 1);
    push(&head, 3);
    push(&head, 2);
    printList(head);
    return 0;
}`,
          status: "accepted",
          score: 90,
          tests_passed: 9,
          tests_total: 10,
          execution_time_ms: 12,
          ai_score: 10,
          plagiarism_score: 5,
          submitted_at: new Date(Date.now() - 172800000).toISOString(),
          review_status: "approved",
        },
      ];
      setSubmissions(demoSubmissions);
    } finally {
      setLoading(false);
    }
  };

  const fetchSubmissionDetails = async (subId: string) => {
    try {
      const [commentsRes, versionsRes] = await Promise.all([
        apiClient.get(`/faculty/submissions/${subId}/comments`),
        apiClient.get(`/faculty/submissions/${subId}/versions`),
      ]);
      setComments(commentsRes.data || []);
      setVersions(versionsRes.data || []);
    } catch (error) {
      console.error("Error fetching submission details:", error);
      // Demo comments
      setComments([
        {
          id: "c1",
          line_number: 15,
          content: "Good use of recursion here. Consider adding a docstring.",
          author: "Dr. Smith",
          created_at: new Date(Date.now() - 3600000).toISOString(),
        },
      ]);
      // Demo versions
      setVersions([
        {
          id: "v1",
          version: 1,
          code: "# Initial implementation...",
          submitted_at: new Date(Date.now() - 7200000).toISOString(),
          tests_passed: 5,
          tests_total: 10,
        },
        {
          id: "v2",
          version: 2,
          code: selectedSubmission?.code || "",
          submitted_at: new Date().toISOString(),
          tests_passed: 8,
          tests_total: 10,
        },
      ]);
    }
  };

  const handleEditorMount = (editor: any) => {
    editorRef.current = editor;

    // Add click listener for line selection
    editor.onMouseDown((e: any) => {
      if (e.target.type === 2) {
        // Line number click
        const lineNumber = e.target.position.lineNumber;
        setSelectedLine(lineNumber);
      }
    });

    // Add decorations for existing comments
    updateDecorations(editor);
  };

  const updateDecorations = (editor: any) => {
    if (!editor) return;

    const decorations = comments.map((comment) => ({
      range: {
        startLineNumber: comment.line_number,
        startColumn: 1,
        endLineNumber: comment.line_number,
        endColumn: 1,
      },
      options: {
        isWholeLine: true,
        className: "bg-blue-500/10",
        glyphMarginClassName: "comment-glyph",
        glyphMarginHoverMessage: { value: `**${comment.author}:** ${comment.content}` },
      },
    }));

    editor.deltaDecorations([], decorations);
  };

  const addComment = async () => {
    if (!selectedLine || !newComment.trim() || !selectedSubmission) return;

    try {
      await apiClient.post(`/faculty/submissions/${selectedSubmission.id}/comments`, {
        line_number: selectedLine,
        content: newComment,
      });

      const newCommentObj: CodeComment = {
        id: `c-${Date.now()}`,
        line_number: selectedLine,
        content: newComment,
        author: user?.full_name || user?.email || "Faculty",
        created_at: new Date().toISOString(),
      };

      setComments([...comments, newCommentObj]);
      setNewComment("");
      setSelectedLine(null);

      if (editorRef.current) {
        updateDecorations(editorRef.current);
      }
    } catch (error) {
      console.error("Error adding comment:", error);
      // Still add locally for demo
      const newCommentObj: CodeComment = {
        id: `c-${Date.now()}`,
        line_number: selectedLine,
        content: newComment,
        author: user?.full_name || user?.email || "Faculty",
        created_at: new Date().toISOString(),
      };
      setComments([...comments, newCommentObj]);
      setNewComment("");
      setSelectedLine(null);
    }
  };

  const deleteComment = async (commentId: string) => {
    try {
      await apiClient.delete(`/faculty/comments/${commentId}`);
      setComments(comments.filter((c) => c.id !== commentId));
    } catch (error) {
      console.error("Error deleting comment:", error);
      setComments(comments.filter((c) => c.id !== commentId));
    }
  };

  const updateReviewStatus = async (status: "approved" | "rejected" | "needs_revision") => {
    if (!selectedSubmission) return;

    try {
      await apiClient.put(`/faculty/submissions/${selectedSubmission.id}/review`, {
        status,
        comments: comments,
      });

      setSelectedSubmission({ ...selectedSubmission, review_status: status });
      setSubmissions(
        submissions.map((s) => (s.id === selectedSubmission.id ? { ...s, review_status: status } : s))
      );
    } catch (error) {
      console.error("Error updating review status:", error);
      setSelectedSubmission({ ...selectedSubmission, review_status: status });
      setSubmissions(
        submissions.map((s) => (s.id === selectedSubmission.id ? { ...s, review_status: status } : s))
      );
    }
  };

  const downloadCode = () => {
    if (!selectedSubmission) return;

    const blob = new Blob([selectedSubmission.code], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${selectedSubmission.student_name.replace(/\s+/g, "_")}_${selectedSubmission.problem_title.replace(/\s+/g, "_")}.${getFileExtension(selectedSubmission.language)}`;
    a.click();
  };

  const getFileExtension = (language: string) => {
    const extensions: Record<string, string> = {
      python: "py",
      javascript: "js",
      java: "java",
      c: "c",
      cpp: "cpp",
      csharp: "cs",
    };
    return extensions[language] || "txt";
  };

  const getLanguageForMonaco = (language: string) => {
    const mapping: Record<string, string> = {
      python: "python",
      javascript: "javascript",
      java: "java",
      c: "c",
      cpp: "cpp",
      csharp: "csharp",
    };
    return mapping[language] || "plaintext";
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "approved":
        return "text-green-500 bg-green-500/10";
      case "rejected":
        return "text-red-500 bg-red-500/10";
      case "needs_revision":
        return "text-yellow-500 bg-yellow-500/10";
      default:
        return "text-gray-400 bg-gray-500/10";
    }
  };

  const filteredSubmissions = submissions.filter(
    (sub) => filterStatus === "all" || sub.review_status === filterStatus
  );

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="h-full text-white flex">
      {/* Sidebar - Submissions List */}
      <div
        className={`${sidebarOpen ? "w-80" : "w-0"} transition-all duration-300 border-r border-gray-700 overflow-hidden flex-shrink-0`}
      >
        <div className="p-4 border-b border-gray-700">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Code className="w-5 h-5 text-blue-500" />
            Submissions
          </h2>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="w-full mt-3 bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm"
          >
            <option value="all">All Status</option>
            <option value="pending">Pending Review</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="needs_revision">Needs Revision</option>
          </select>
        </div>

        <div className="overflow-y-auto scrollbar-hide h-[calc(100vh-120px)]">
          {filteredSubmissions.map((sub) => (
            <div
              key={sub.id}
              onClick={() => {
                setSelectedSubmission(sub);
                fetchSubmissionDetails(sub.id);
              }}
              className={`p-4 border-b border-gray-700/50 cursor-pointer hover:bg-gray-800 ${
                selectedSubmission?.id === sub.id ? "bg-gray-800" : ""
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="font-medium">{sub.student_name}</div>
                  <div className="text-sm text-gray-400 mt-1">{sub.problem_title}</div>
                  <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
                    <Clock className="w-3 h-3" />
                    {new Date(sub.submitted_at).toLocaleDateString()}
                  </div>
                </div>
                <span
                  className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(sub.review_status)}`}
                >
                  {sub.review_status}
                </span>
              </div>

              {/* Risk indicators */}
              <div className="flex items-center gap-3 mt-2">
                {sub.ai_score >= 60 && (
                  <span className="flex items-center gap-1 text-xs text-red-400">
                    <Bot className="w-3 h-3" />
                    AI: {sub.ai_score}%
                  </span>
                )}
                {sub.plagiarism_score >= 50 && (
                  <span className="flex items-center gap-1 text-xs text-orange-400">
                    <Copy className="w-3 h-3" />
                    Plag: {sub.plagiarism_score}%
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Toggle Sidebar Button */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="absolute left-0 top-1/2 transform -translate-y-1/2 z-10 bg-gray-800 p-2 rounded-r-lg border border-l-0 border-gray-700"
        style={{ left: sidebarOpen ? "320px" : "0" }}
      >
        {sidebarOpen ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
      </button>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {selectedSubmission ? (
          <>
            {/* Header */}
            <div className="p-4 border-b border-gray-700 bg-gray-800">
              <div className="flex items-center justify-between">
                <div>
                  <h1 className="text-xl font-bold">{selectedSubmission.problem_title}</h1>
                  <div className="flex items-center gap-4 mt-2 text-sm text-gray-400">
                    <span className="flex items-center gap-1">
                      <User className="w-4 h-4" />
                      {selectedSubmission.student_name}
                    </span>
                    <span className="flex items-center gap-1">
                      <FileCode className="w-4 h-4" />
                      {selectedSubmission.language.toUpperCase()}
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-4 h-4" />
                      {new Date(selectedSubmission.submitted_at).toLocaleString()}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  {/* Analysis Scores */}
                  <div className="flex items-center gap-4 px-4 py-2 bg-gray-900 rounded-lg">
                    <div className="flex items-center gap-2">
                      <Bot className="w-4 h-4 text-purple-500" />
                      <span
                        className={`font-semibold ${selectedSubmission.ai_score >= 60 ? "text-red-500" : selectedSubmission.ai_score >= 30 ? "text-yellow-500" : "text-green-500"}`}
                      >
                        {selectedSubmission.ai_score}%
                      </span>
                    </div>
                    <div className="w-px h-6 bg-gray-700"></div>
                    <div className="flex items-center gap-2">
                      <Copy className="w-4 h-4 text-orange-500" />
                      <span
                        className={`font-semibold ${selectedSubmission.plagiarism_score >= 50 ? "text-red-500" : selectedSubmission.plagiarism_score >= 20 ? "text-yellow-500" : "text-green-500"}`}
                      >
                        {selectedSubmission.plagiarism_score}%
                      </span>
                    </div>
                  </div>

                  {/* Version Compare */}
                  <button
                    onClick={() => setShowDiff(!showDiff)}
                    className={`p-2 rounded-lg ${showDiff ? "bg-blue-600" : "bg-gray-700"} hover:bg-blue-600`}
                    title="Compare Versions"
                  >
                    <GitCompare className="w-5 h-5" />
                  </button>

                  {/* Download */}
                  <button
                    onClick={downloadCode}
                    className="p-2 bg-gray-700 rounded-lg hover:bg-gray-600"
                    title="Download Code"
                  >
                    <Download className="w-5 h-5" />
                  </button>
                </div>
              </div>

              {/* Test Results */}
              <div className="flex items-center gap-4 mt-4">
                <div className="flex items-center gap-2">
                  <Play className="w-4 h-4 text-green-500" />
                  <span className="text-sm">
                    Tests: {selectedSubmission.tests_passed}/{selectedSubmission.tests_total} passed
                  </span>
                </div>
                <div className="flex-1 bg-gray-700 rounded-full h-2">
                  <div
                    className="bg-green-500 h-2 rounded-full"
                    style={{
                      width: `${(selectedSubmission.tests_passed / selectedSubmission.tests_total) * 100}%`,
                    }}
                  ></div>
                </div>
                <span className="text-sm text-gray-400">
                  Score: <span className="text-white font-semibold">{selectedSubmission.score}/100</span>
                </span>
                <span className="text-sm text-gray-400">
                  Time: <span className="text-white">{selectedSubmission.execution_time_ms}ms</span>
                </span>
              </div>
            </div>

            {/* Code Editor & Comments */}
            <div className="flex-1 flex">
              {/* Code Editor */}
              <div className="flex-1 relative">
                {showDiff && versions.length >= 2 ? (
                  <div className="h-full flex flex-col">
                    <div className="p-2 bg-gray-800 border-b border-gray-700 flex items-center gap-4">
                      <span className="text-sm text-gray-400">Compare with:</span>
                      <select
                        value={diffVersion || ""}
                        onChange={(e) => setDiffVersion(e.target.value)}
                        className="bg-gray-700 border border-gray-600 rounded px-3 py-1 text-sm"
                      >
                        {versions.slice(0, -1).map((v) => (
                          <option key={v.id} value={v.id}>
                            Version {v.version} ({new Date(v.submitted_at).toLocaleString()})
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="flex-1">
                      <MonacoEditor
                        height="100%"
                        language={getLanguageForMonaco(selectedSubmission.language)}
                        value={selectedSubmission.code}
                        theme="vs-dark"
                        options={{
                          readOnly: true,
                          minimap: { enabled: false },
                          fontSize: 14,
                          lineNumbers: "on",
                          scrollBeyondLastLine: false,
                        }}
                        onMount={handleEditorMount}
                      />
                    </div>
                  </div>
                ) : (
                  <MonacoEditor
                    height="100%"
                    language={getLanguageForMonaco(selectedSubmission.language)}
                    value={selectedSubmission.code}
                    theme="vs-dark"
                    options={{
                      readOnly: true,
                      minimap: { enabled: false },
                      fontSize: 14,
                      lineNumbers: "on",
                      scrollBeyondLastLine: false,
                      glyphMargin: true,
                    }}
                    onMount={handleEditorMount}
                  />
                )}

                {/* Line Comment Input */}
                {selectedLine && (
                  <div className="absolute bottom-4 left-4 right-4 bg-gray-800 rounded-lg p-4 shadow-xl border border-gray-700">
                    <div className="flex items-center gap-2 mb-2 text-sm text-gray-400">
                      <MessageSquare className="w-4 h-4" />
                      Add comment on line {selectedLine}
                    </div>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={newComment}
                        onChange={(e) => setNewComment(e.target.value)}
                        placeholder="Type your comment..."
                        className="flex-1 bg-gray-700 border border-gray-600 rounded px-3 py-2"
                        onKeyDown={(e) => e.key === "Enter" && addComment()}
                      />
                      <button
                        onClick={addComment}
                        className="px-4 py-2 bg-blue-600 rounded hover:bg-blue-700"
                      >
                        <Send className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => {
                          setSelectedLine(null);
                          setNewComment("");
                        }}
                        className="px-4 py-2 bg-gray-700 rounded hover:bg-gray-600"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* Comments Sidebar */}
              <div className="w-80 border-l border-gray-700 flex flex-col">
                <div className="p-4 border-b border-gray-700 bg-gray-800">
                  <h3 className="font-semibold flex items-center gap-2">
                    <MessageSquare className="w-4 h-4" />
                    Comments ({comments.length})
                  </h3>
                  <p className="text-xs text-gray-400 mt-1">Click on line numbers to add comments</p>
                </div>

                <div className="flex-1 overflow-y-auto scrollbar-hide p-4 space-y-3">
                  {comments.length === 0 ? (
                    <div className="text-center text-gray-500 py-8">
                      <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
                      <p>No comments yet</p>
                      <p className="text-xs mt-1">Click on a line number to add feedback</p>
                    </div>
                  ) : (
                    comments.map((comment) => (
                      <div
                        key={comment.id}
                        className="bg-gray-800 rounded-lg p-3 border border-gray-700"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex items-center gap-2 text-xs text-gray-400">
                            <span className="px-2 py-0.5 bg-blue-600/20 text-blue-400 rounded">
                              Line {comment.line_number}
                            </span>
                            <span>{comment.author}</span>
                          </div>
                          <button
                            onClick={() => deleteComment(comment.id)}
                            className="text-gray-500 hover:text-red-500"
                          >
                            <Trash2 className="w-3 h-3" />
                          </button>
                        </div>
                        <p className="mt-2 text-sm">{comment.content}</p>
                        <div className="text-xs text-gray-500 mt-2">
                          {new Date(comment.created_at).toLocaleString()}
                        </div>
                      </div>
                    ))
                  )}
                </div>

                {/* Review Actions */}
                <div className="p-4 border-t border-gray-700 bg-gray-800 space-y-3">
                  <div className="text-sm text-gray-400 mb-2">Review Decision:</div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => updateReviewStatus("approved")}
                      className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg ${
                        selectedSubmission.review_status === "approved"
                          ? "bg-green-600"
                          : "bg-gray-700 hover:bg-green-600/50"
                      }`}
                    >
                      <CheckCircle className="w-4 h-4" />
                      Approve
                    </button>
                    <button
                      onClick={() => updateReviewStatus("rejected")}
                      className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg ${
                        selectedSubmission.review_status === "rejected"
                          ? "bg-red-600"
                          : "bg-gray-700 hover:bg-red-600/50"
                      }`}
                    >
                      <XCircle className="w-4 h-4" />
                      Reject
                    </button>
                  </div>
                  <button
                    onClick={() => updateReviewStatus("needs_revision")}
                    className={`w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg ${
                      selectedSubmission.review_status === "needs_revision"
                        ? "bg-yellow-600"
                        : "bg-gray-700 hover:bg-yellow-600/50"
                    }`}
                  >
                    <AlertTriangle className="w-4 h-4" />
                    Request Revision
                  </button>
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-500">
            <div className="text-center">
              <Eye className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p className="text-lg">Select a submission to review</p>
              <p className="text-sm mt-2">Choose from the list on the left</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function CodeReviewPage() {
  return (
    <Suspense
      fallback={
        <div className="h-full flex items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
        </div>
      }
    >
      <CodeReviewContent />
    </Suspense>
  );
}
