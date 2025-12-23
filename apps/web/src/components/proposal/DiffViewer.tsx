'use client'

import { useState } from 'react'
import ReactDiffViewer, { DiffMethod } from 'react-diff-viewer-continued'

interface DiffViewerProps {
  originalContent: string
  newContent: string
  fileName: string
  onClose: () => void
}

export function DiffViewer({ originalContent, newContent, fileName, onClose }: DiffViewerProps) {
  const [splitView, setSplitView] = useState(true)

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-[90vw] h-[85vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b bg-gray-50 rounded-t-lg">
          <div className="flex items-center gap-4">
            <h3 className="font-semibold text-gray-900">{fileName}</h3>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setSplitView(true)}
                className={`px-3 py-1 text-sm rounded ${
                  splitView ? 'bg-gray-200 text-gray-900' : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                Split
              </button>
              <button
                onClick={() => setSplitView(false)}
                className={`px-3 py-1 text-sm rounded ${
                  !splitView ? 'bg-gray-200 text-gray-900' : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                Unified
              </button>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 p-1"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Diff Content */}
        <div className="flex-1 overflow-auto">
          <ReactDiffViewer
            oldValue={originalContent}
            newValue={newContent}
            splitView={splitView}
            compareMethod={DiffMethod.WORDS}
            leftTitle="Original"
            rightTitle="Proposed"
            styles={{
              variables: {
                light: {
                  diffViewerBackground: '#fff',
                  addedBackground: '#e6ffec',
                  addedColor: '#24292f',
                  removedBackground: '#ffebe9',
                  removedColor: '#24292f',
                  wordAddedBackground: '#abf2bc',
                  wordRemovedBackground: '#ff8182',
                  addedGutterBackground: '#ccffd8',
                  removedGutterBackground: '#ffd7d5',
                  gutterBackground: '#f6f8fa',
                  gutterBackgroundDark: '#f0f1f3',
                  highlightBackground: '#fffbdd',
                  highlightGutterBackground: '#fff5b1',
                },
              },
              line: {
                padding: '4px 8px',
                fontSize: '13px',
                fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace',
              },
              gutter: {
                minWidth: '40px',
              },
            }}
          />
        </div>
      </div>
    </div>
  )
}
