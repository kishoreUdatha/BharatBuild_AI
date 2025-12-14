'use client';

import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useDropzone } from 'react-dropzone';

interface PaperAnalysis {
  paper_info?: {
    title: string;
    domain: string;
    abstract_summary: string;
  };
  problem_statement?: {
    description: string;
    proposed_solution: string;
  };
  technologies?: {
    programming_languages: string[];
    frameworks: string[];
    algorithms: string[];
  };
  implementation_plan?: {
    project_type: string;
    core_features: Array<{ feature: string; priority: string }>;
  };
}

export default function PaperUploadPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [paperTitle, setPaperTitle] = useState('');
  const [projectName, setProjectName] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [analysis, setAnalysis] = useState<PaperAnalysis | null>(null);
  const [analysisText, setAnalysisText] = useState('');
  const [generatedPrompt, setGeneratedPrompt] = useState('');
  const [error, setError] = useState('');
  const [step, setStep] = useState(1);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const pdfFile = acceptedFiles.find(f => f.name.toLowerCase().endsWith('.pdf'));
    if (pdfFile) {
      setFile(pdfFile);
      setPaperTitle(pdfFile.name.replace('.pdf', '').replace(/_/g, ' ').replace(/-/g, ' '));
      setError('');
    } else {
      setError('Please upload a PDF file');
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 1,
    maxSize: 10 * 1024 * 1024 // 10MB
  });

  const analyzePaper = async () => {
    if (!file) return;

    setIsAnalyzing(true);
    setError('');
    setAnalysisText('');

    try {
      const formData = new FormData();
      formData.append('file', file);
      if (paperTitle) formData.append('paper_title', paperTitle);

      const token = localStorage.getItem('access_token');
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/paper/analyze`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });

      if (!response.ok) throw new Error('Analysis failed');

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let fullText = '';

      while (reader) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.type === 'content') {
                fullText += data.text;
                setAnalysisText(fullText);
              } else if (data.type === 'error') {
                setError(data.message);
              }
            } catch {}
          }
        }
      }

      // Try to parse JSON from response
      try {
        const jsonMatch = fullText.match(/```json\s*([\s\S]*?)\s*```/);
        if (jsonMatch) {
          setAnalysis(JSON.parse(jsonMatch[1]));
        }
      } catch {}

      setStep(2);
    } catch (err: any) {
      setError(err.message || 'Failed to analyze paper');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const generateProject = async () => {
    if (!file) return;

    setIsGenerating(true);
    setError('');

    try {
      const formData = new FormData();
      formData.append('file', file);
      if (paperTitle) formData.append('paper_title', paperTitle);
      if (projectName) formData.append('project_name', projectName);

      const token = localStorage.getItem('access_token');
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/paper/generate-project`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });

      if (!response.ok) throw new Error('Project generation failed');

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      while (reader) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.type === 'status') {
                setStep(data.step || step);
              } else if (data.type === 'prompt') {
                setGeneratedPrompt(data.text);
              } else if (data.type === 'analysis') {
                setAnalysis(data.data);
              } else if (data.type === 'done') {
                // Redirect to bolt with the generated prompt
                if (data.project_id) {
                  localStorage.setItem('paper_prompt', data.prompt);
                  router.push(`/build?paper_project=${data.project_id}`);
                }
              } else if (data.type === 'error') {
                setError(data.message);
              }
            } catch {}
          }
        }
      }
    } catch (err: any) {
      setError(err.message || 'Failed to generate project');
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-gray-900">
      {/* Header */}
      <header className="border-b border-gray-800 bg-black/30 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg flex items-center justify-center">
              <span className="text-xl font-bold text-white">B</span>
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">BharatBuild AI</h1>
              <p className="text-xs text-gray-400">IEEE Paper to Project</p>
            </div>
          </div>
          <button
            onClick={() => router.push('/build')}
            className="px-4 py-2 text-sm text-gray-300 hover:text-white transition-colors"
          >
            Back to Editor
          </button>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-8">
        {/* Progress Steps */}
        <div className="flex items-center justify-center gap-4 mb-8">
          {[1, 2, 3].map((s) => (
            <div key={s} className="flex items-center gap-2">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                step >= s ? 'bg-purple-600 text-white' : 'bg-gray-700 text-gray-400'
              }`}>
                {s}
              </div>
              <span className={`text-sm ${step >= s ? 'text-white' : 'text-gray-500'}`}>
                {s === 1 ? 'Upload Paper' : s === 2 ? 'Review Analysis' : 'Generate Project'}
              </span>
              {s < 3 && <div className={`w-12 h-0.5 ${step > s ? 'bg-purple-600' : 'bg-gray-700'}`} />}
            </div>
          ))}
        </div>

        {/* Step 1: Upload */}
        {step === 1 && (
          <div className="space-y-6">
            <div className="text-center mb-8">
              <h2 className="text-3xl font-bold text-white mb-2">Upload IEEE Base Paper</h2>
              <p className="text-gray-400">
                Upload your research paper and we'll automatically generate a working project with documentation
              </p>
            </div>

            {/* Dropzone */}
            <div
              {...getRootProps()}
              className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all ${
                isDragActive
                  ? 'border-purple-500 bg-purple-500/10'
                  : file
                  ? 'border-green-500 bg-green-500/10'
                  : 'border-gray-600 hover:border-purple-500 hover:bg-purple-500/5'
              }`}
            >
              <input {...getInputProps()} />
              {file ? (
                <div>
                  <div className="w-16 h-16 mx-auto mb-4 bg-green-500/20 rounded-full flex items-center justify-center">
                    <svg className="w-8 h-8 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <p className="text-lg font-medium text-white">{file.name}</p>
                  <p className="text-sm text-gray-400 mt-1">
                    {(file.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                  <button
                    onClick={(e) => { e.stopPropagation(); setFile(null); }}
                    className="mt-4 text-sm text-red-400 hover:text-red-300"
                  >
                    Remove file
                  </button>
                </div>
              ) : (
                <div>
                  <div className="w-16 h-16 mx-auto mb-4 bg-purple-500/20 rounded-full flex items-center justify-center">
                    <svg className="w-8 h-8 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                  </div>
                  <p className="text-lg font-medium text-white">
                    {isDragActive ? 'Drop your paper here' : 'Drag & drop your IEEE paper'}
                  </p>
                  <p className="text-sm text-gray-400 mt-1">or click to browse (PDF only, max 10MB)</p>
                </div>
              )}
            </div>

            {/* Paper Title Input */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Paper Title (optional)
              </label>
              <input
                type="text"
                value={paperTitle}
                onChange={(e) => setPaperTitle(e.target.value)}
                placeholder="Enter paper title or leave blank to auto-detect"
                className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
              />
            </div>

            {error && (
              <div className="p-4 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400">
                {error}
              </div>
            )}

            {/* Analyze Button */}
            <button
              onClick={analyzePaper}
              disabled={!file || isAnalyzing}
              className="w-full py-4 bg-gradient-to-r from-purple-600 to-pink-600 text-white font-medium rounded-lg hover:from-purple-700 hover:to-pink-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              {isAnalyzing ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Analyzing Paper...
                </span>
              ) : (
                'Analyze Paper'
              )}
            </button>

            {/* Features */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8">
              {[
                { icon: '📄', title: 'Extract Requirements', desc: 'Auto-extract problem statement, methodology, tech stack' },
                { icon: '💻', title: 'Generate Code', desc: 'Full working project based on paper architecture' },
                { icon: '📚', title: 'Create Documentation', desc: 'SRS, SDS, UML diagrams, reports, and PPT' }
              ].map((feature, i) => (
                <div key={i} className="p-4 bg-gray-800/50 rounded-lg border border-gray-700">
                  <div className="text-2xl mb-2">{feature.icon}</div>
                  <h3 className="font-medium text-white">{feature.title}</h3>
                  <p className="text-sm text-gray-400">{feature.desc}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Step 2: Review Analysis */}
        {step === 2 && (
          <div className="space-y-6">
            <div className="text-center mb-8">
              <h2 className="text-3xl font-bold text-white mb-2">Paper Analysis</h2>
              <p className="text-gray-400">Review the extracted requirements before generating the project</p>
            </div>

            {/* Analysis Output */}
            <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-6 max-h-96 overflow-y-auto">
              <pre className="text-sm text-gray-300 whitespace-pre-wrap font-mono">
                {analysisText || 'No analysis available'}
              </pre>
            </div>

            {/* Extracted Info Cards */}
            {analysis && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {analysis.paper_info && (
                  <div className="p-4 bg-gray-800/50 rounded-lg border border-gray-700">
                    <h3 className="font-medium text-purple-400 mb-2">Paper Info</h3>
                    <p className="text-white font-medium">{analysis.paper_info.title}</p>
                    <p className="text-sm text-gray-400">Domain: {analysis.paper_info.domain}</p>
                  </div>
                )}
                {analysis.technologies && (
                  <div className="p-4 bg-gray-800/50 rounded-lg border border-gray-700">
                    <h3 className="font-medium text-purple-400 mb-2">Technologies</h3>
                    <div className="flex flex-wrap gap-2">
                      {[
                        ...(analysis.technologies.programming_languages || []),
                        ...(analysis.technologies.frameworks || []),
                        ...(analysis.technologies.algorithms || [])
                      ].slice(0, 8).map((tech, i) => (
                        <span key={i} className="px-2 py-1 bg-purple-500/20 text-purple-300 text-xs rounded">
                          {tech}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Project Name */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Project Name
              </label>
              <input
                type="text"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                placeholder="Enter a name for your project"
                className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
              />
            </div>

            {error && (
              <div className="p-4 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400">
                {error}
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex gap-4">
              <button
                onClick={() => setStep(1)}
                className="flex-1 py-4 bg-gray-700 text-white font-medium rounded-lg hover:bg-gray-600 transition-colors"
              >
                Back
              </button>
              <button
                onClick={generateProject}
                disabled={isGenerating}
                className="flex-1 py-4 bg-gradient-to-r from-purple-600 to-pink-600 text-white font-medium rounded-lg hover:from-purple-700 hover:to-pink-700 disabled:opacity-50 transition-all"
              >
                {isGenerating ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Generating Project...
                  </span>
                ) : (
                  'Generate Project & Docs'
                )}
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Generating */}
        {step === 3 && (
          <div className="text-center py-12">
            <div className="w-20 h-20 mx-auto mb-6 bg-purple-500/20 rounded-full flex items-center justify-center">
              <svg className="animate-spin h-10 w-10 text-purple-500" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-white mb-2">Creating Your Project</h2>
            <p className="text-gray-400">This may take a few moments...</p>

            {generatedPrompt && (
              <div className="mt-8 text-left bg-gray-800/50 rounded-lg border border-gray-700 p-6 max-h-64 overflow-y-auto">
                <h3 className="font-medium text-purple-400 mb-2">Generated Project Prompt</h3>
                <pre className="text-sm text-gray-300 whitespace-pre-wrap">{generatedPrompt}</pre>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
