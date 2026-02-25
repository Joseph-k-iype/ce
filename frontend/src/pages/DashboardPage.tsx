import { useState } from 'react';
import { ExcelUploader } from '../components/dashboard/ExcelUploader';
import { LogicBuilder } from '../components/dashboard/LogicBuilder';
import { TaxonomyManager } from '../components/dashboard/TaxonomyManager';

export function DashboardPage() {
    const [activeTab, setActiveTab] = useState<'upload' | 'builder' | 'taxonomy'>('upload');

    return (
        <div className="flex-1 flex flex-col h-full bg-slate-50">
            <div className="bg-white border-b border-gray-200 px-8 py-6 flex items-center justify-between shadow-sm relative overflow-hidden">
                <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-purple-400 via-purple-500 to-purple-600"></div>
                <div className="relative z-10">
                    <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Rules Administration</h1>
                    <p className="text-sm text-gray-500 mt-1.5 font-medium">
                        Upload Excel policy maps or visually edit complex compliance logic.
                    </p>
                </div>
                <div className="flex bg-slate-100 p-1.5 rounded-xl shadow-inner relative z-10">
                    <button
                        onClick={() => setActiveTab('upload')}
                        className={`px-5 py-2.5 text-sm font-semibold rounded-lg transition-all duration-200 flex items-center gap-2 ${activeTab === 'upload' ? 'bg-white shadow-md text-purple-700' : 'text-slate-600 hover:text-purple-600 hover:bg-slate-200/50'
                            }`}
                    >
                        Excel Upload
                    </button>
                    <button
                        onClick={() => setActiveTab('builder')}
                        className={`px-5 py-2.5 text-sm font-semibold rounded-lg transition-all duration-200 flex items-center gap-2 ${activeTab === 'builder' ? 'bg-white shadow-md text-purple-700' : 'text-slate-600 hover:text-purple-600 hover:bg-slate-200/50'
                            }`}
                    >
                        Logic Builder
                    </button>
                    <button
                        onClick={() => setActiveTab('taxonomy')}
                        className={`px-5 py-2.5 text-sm font-semibold rounded-lg transition-all duration-200 flex items-center gap-2 ${activeTab === 'taxonomy' ? 'bg-white shadow-md text-purple-700' : 'text-slate-600 hover:text-purple-600 hover:bg-slate-200/50'
                            }`}
                    >
                        Taxonomy
                    </button>
                </div>
            </div>

            <div className="flex-1 overflow-hidden relative">
                {activeTab === 'upload' && (
                    <div className="absolute inset-0 p-8 overflow-y-auto w-full h-full animate-in fade-in slide-in-from-bottom-2 duration-300">
                        <ExcelUploader />
                    </div>
                )}
                {activeTab === 'builder' && (
                    <div className="absolute inset-0 p-8 overflow-y-auto w-full h-full animate-in fade-in slide-in-from-bottom-2 duration-300 bg-white">
                        <LogicBuilder />
                    </div>
                )}
                {activeTab === 'taxonomy' && (
                    <div className="absolute inset-0 p-8 overflow-y-auto w-full h-full animate-in fade-in slide-in-from-bottom-2 duration-300 bg-slate-50">
                        <TaxonomyManager />
                    </div>
                )}
            </div>
        </div>
    );
}
