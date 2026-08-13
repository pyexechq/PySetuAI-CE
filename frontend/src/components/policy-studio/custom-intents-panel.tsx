"use client";

import { useState } from "react";
import { Plus, Trash2, Edit, ShieldAlert, Eye, Scissors, Play, Loader2, Sparkles, Folder, FolderPlus } from "lucide-react";
import {
  useCustomIntents,
  useCreateCustomIntent,
  useUpdateCustomIntent,
  useDeleteCustomIntent,
} from "@/hooks/use-custom-intents";
import { Button } from "@/components/ui/button";
import { AppModal } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { CustomIntent } from "@/lib/types/domain";
import type { ApiCustomIntentAssistSuggestion } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import { CustomIntentAiHelper } from "./custom-intent-ai-helper";
import { CustomIntentTesterModal } from "./custom-intent-tester-modal";

export function CustomIntentsPanel() {
  const token = useAuthStore((s) => s.token);
  const { data: intents = [], isLoading } = useCustomIntents();
  const createMutation = useCreateCustomIntent();
  const updateMutation = useUpdateCustomIntent();
  const deleteMutation = useDeleteCustomIntent();

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isFolderModalOpen, setIsFolderModalOpen] = useState(false);
  const [isTesterModalOpen, setIsTesterModalOpen] = useState(false);
  const [editingIntent, setEditingIntent] = useState<CustomIntent | null>(null);
  
  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(null);

  // Form State
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [action, setAction] = useState<"block" | "monitor" | "redact">("block");
  const [keywords, setKeywords] = useState<string[]>([]);
  const [newKeyword, setNewKeyword] = useState("");
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.8);
  const [parentId, setParentId] = useState<string | null>(null);
  const [folderName, setFolderName] = useState("");

  const folders = intents.filter((i) => i.intent_type === "folder");
  
  const displayedIntents = intents.filter((i) => {
    if (i.intent_type === "folder") return false;
    if (selectedFolderId === null) return true; // All intents
    return i.parent_id === selectedFolderId;
  });

  const openCreateModal = (defaultParentId: string | null = null) => {
    setEditingIntent(null);
    setName("");
    setDescription("");
    setAction("block");
    setKeywords([]);
    setConfidenceThreshold(0.8);
    setParentId(defaultParentId);
    setIsModalOpen(true);
  };

  const openCreateFolderModal = () => {
    setFolderName("");
    setIsFolderModalOpen(true);
  };

  const handleCreateFolder = (e: React.FormEvent) => {
    e.preventDefault();
    if (!folderName.trim()) return;
    createMutation.mutate(
      {
        name: folderName.trim(),
        description: "Folder for grouping intent classifiers",
        action: "monitor",
        keywords: [],
        confidence_threshold: 0.8,
        intent_type: "folder",
      },
      {
        onSuccess: () => {
          setIsFolderModalOpen(false);
          setFolderName("");
        },
      }
    );
  };

  const openEditModal = (intent: CustomIntent) => {
    setEditingIntent(intent);
    setName(intent.name);
    setDescription(intent.description || "");
    setAction(intent.action);
    setKeywords(intent.keywords || []);
    setConfidenceThreshold(intent.confidence_threshold);
    setParentId(intent.parent_id || null);
    setIsModalOpen(true);
  };

  const handleApplySuggestion = (suggestion: ApiCustomIntentAssistSuggestion) => {
    setEditingIntent(null);
    setName(suggestion.name);
    setDescription(suggestion.description);
    setAction(suggestion.action as any);
    setKeywords(suggestion.keywords);
    setConfidenceThreshold(suggestion.confidence_threshold);
    setParentId(selectedFolderId);
    setIsModalOpen(true);
  };

  const handleAddKeyword = () => {
    if (newKeyword.trim() && !keywords.includes(newKeyword.trim())) {
      setKeywords([...keywords, newKeyword.trim()]);
      setNewKeyword("");
    }
  };

  const handleRemoveKeyword = (kw: string) => {
    setKeywords(keywords.filter((k) => k !== kw));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    if (editingIntent) {
      updateMutation.mutate(
        {
          id: editingIntent.id,
          data: {
            name,
            description,
            action,
            keywords,
            confidence_threshold: confidenceThreshold,
            parent_id: parentId,
          },
        },
        {
          onSuccess: () => setIsModalOpen(false),
        }
      );
    } else {
      createMutation.mutate(
        {
          name,
          description,
          action,
          keywords,
          confidence_threshold: confidenceThreshold,
          parent_id: parentId,
          intent_type: "intent",
        },
        {
          onSuccess: () => setIsModalOpen(false),
        }
      );
    }
  };

  const getActionBadge = (act: string) => {
    if (act === "block") {
      return (
        <Badge variant="destructive" className="gap-1 bg-destructive/10 text-destructive border-destructive/20 text-[10px] px-1.5 h-5">
          <ShieldAlert className="h-3 w-3" />
          Block
        </Badge>
      );
    }
    if (act === "redact") {
      return (
        <Badge variant="outline" className="gap-1 border-purple-500/40 text-purple-400 text-[10px] px-1.5 h-5">
          <Scissors className="h-3 w-3" />
          Redact
        </Badge>
      );
    }
    return (
      <Badge variant="secondary" className="gap-1 text-[10px] px-1.5 h-5">
        <Eye className="h-3 w-3" />
        Monitor
      </Badge>
    );
  };

  return (
    <div className="flex h-[calc(100vh-11rem)] gap-4">
      {/* Left Sidebar: Folders */}
      <Card className="w-72 shrink-0 border-border/60 bg-card/50 flex flex-col min-h-0">
        <CardHeader className="pb-3 shrink-0">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm">Intent Folders</CardTitle>
            <Button size="sm" className="h-7 text-xs" onClick={openCreateFolderModal}>
              Create
            </Button>
          </div>
        </CardHeader>
        <CardContent className="flex-1 overflow-y-auto pt-0 space-y-1">
          <button
            className={`w-full text-left px-3 py-2 rounded-md text-sm flex justify-between items-center transition-colors ${
              selectedFolderId === null ? "bg-primary/10 text-primary font-medium" : "hover:bg-muted/50"
            }`}
            onClick={() => setSelectedFolderId(null)}
          >
            <span className="flex items-center gap-2">
              <Folder className="h-4 w-4" /> All Intents
            </span>
            <Badge variant="secondary" className="text-[10px] h-5">
              {intents.filter((i) => i.intent_type !== "folder").length}
            </Badge>
          </button>
          
          <div className="my-2 border-t border-border/50"></div>
          
          {folders.map((f) => {
            const count = intents.filter((i) => i.parent_id === f.id && i.intent_type !== "folder").length;
            return (
              <button
                key={f.id}
                className={`w-full text-left px-3 py-2 rounded-md text-sm flex justify-between items-center group transition-colors ${
                  selectedFolderId === f.id ? "bg-primary/10 text-primary font-medium" : "hover:bg-muted/50"
                }`}
                onClick={() => setSelectedFolderId(f.id)}
              >
                <span className="flex items-center gap-2 truncate">
                  <Folder className="h-4 w-4 shrink-0" />
                  <span className="truncate">{f.name}</span>
                </span>
                <div className="flex items-center gap-1 shrink-0">
                  <Badge variant="secondary" className={`text-[10px] h-5 ${selectedFolderId === f.id ? 'bg-primary/20 text-primary hover:bg-primary/30' : ''}`}>
                    {count}
                  </Badge>
                  <Trash2 
                    className="h-3.5 w-3.5 opacity-0 group-hover:opacity-100 text-destructive hover:text-red-400 transition-opacity ml-1 cursor-pointer" 
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteMutation.mutate(f.id);
                    }} 
                  />
                </div>
              </button>
            );
          })}
        </CardContent>
      </Card>

      {/* Main Area */}
      <Card className="flex-1 flex flex-col overflow-hidden border-border/60 bg-card/50 min-h-0">
        <CardHeader className="pb-4 shrink-0 border-b border-border/60">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <CardTitle className="text-base flex items-center gap-2">
                {selectedFolderId ? (
                  <>
                    <Folder className="h-4 w-4 text-primary" />
                    {folders.find((f) => f.id === selectedFolderId)?.name || "Folder"}
                  </>
                ) : (
                  "All Intent Classifiers"
                )}
              </CardTitle>
              <p className="mt-1 text-xs text-muted-foreground">
                Define custom content classifiers with sample phrases and keywords for policy enforcement.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button onClick={() => setIsTesterModalOpen(true)} variant="outline" size="sm" className="gap-1.5 h-8 text-xs bg-background">
                <Play className="h-3.5 w-3.5 text-primary" />
                Test Classifiers
              </Button>
              <Button onClick={() => openCreateModal(selectedFolderId)} size="sm" className="gap-1.5 h-8 text-xs">
                <Plus className="h-3.5 w-3.5" />
                Create Classifier
              </Button>
            </div>
          </div>
        </CardHeader>
        
        <CardContent className="flex-1 overflow-hidden p-0 flex flex-col lg:flex-row">
          {/* Classifiers List */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3 lg:border-r lg:border-border/60">
            {isLoading ? (
              <div className="p-8 text-center text-sm text-muted-foreground animate-pulse">
                Loading intent classifiers...
              </div>
            ) : displayedIntents.length === 0 ? (
              <div className="flex flex-col items-center justify-center text-center p-8 h-full space-y-3">
                <Sparkles className="h-8 w-8 text-muted-foreground opacity-50" />
                <p className="font-medium text-sm">No custom intents {selectedFolderId ? "in this folder" : "defined"}</p>
                <p className="text-xs text-muted-foreground max-w-sm">
                  Create a custom intent classifier to flag proprietary data, wire transfers, or custom topics.
                </p>
                <Button size="sm" onClick={() => openCreateModal(selectedFolderId)} className="mt-2 h-8 text-xs">
                  <Plus className="h-3.5 w-3.5 mr-1" /> Create Intent
                </Button>
              </div>
            ) : (
              displayedIntents.map((intent) => (
                <div
                  key={intent.id}
                  className="rounded-md border border-border/60 bg-card p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-sm hover:border-primary/20 transition-colors"
                >
                  <div className="space-y-1.5 flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm truncate">{intent.name}</span>
                      {getActionBadge(intent.action)}
                      <span className="text-[10px] text-muted-foreground">
                        Thresh: {Math.round(intent.confidence_threshold * 100)}%
                      </span>
                    </div>
                    {intent.description && (
                      <p className="text-xs text-muted-foreground truncate">{intent.description}</p>
                    )}
                    <div className="flex flex-wrap gap-1 mt-1">
                      {intent.keywords.map((kw) => (
                        <Badge key={kw} variant="outline" className="text-[9px] bg-muted/30 h-4 px-1.5 font-normal">
                          {kw}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <div className="flex items-center gap-1 self-end sm:self-center shrink-0">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => openEditModal(intent)}
                      title="Edit Intent"
                      className="h-7 w-7"
                    >
                      <Edit className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => deleteMutation.mutate(intent.id)}
                      disabled={deleteMutation.isPending}
                      title="Delete Intent"
                      className="h-7 w-7 text-destructive hover:text-destructive hover:bg-destructive/10"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
              ))
            )}
          </div>
          
          {/* AI Helper Sidebar */}
          <div className="w-full lg:w-[320px] shrink-0 p-4 bg-muted/10 overflow-y-auto">
            <CustomIntentAiHelper
              token={token}
              canEdit={true}
              onApplySuggestion={handleApplySuggestion}
            />
          </div>
        </CardContent>
      </Card>

      {/* Create Folder Modal */}
      {isFolderModalOpen && (
        <AppModal
          title="Create Intent Folder"
          description="Organize custom intent classifiers into a folder to bundle them together for API Keys."
          onClose={() => setIsFolderModalOpen(false)}
          size="sm"
        >
            <form onSubmit={handleCreateFolder}>
              <div className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Folder Name</label>
                  <input
                    type="text"
                    required
                    value={folderName}
                    onChange={(e) => setFolderName(e.target.value)}
                    className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none"
                    placeholder="e.g. Prompt Injections & Jailbreaks"
                  />
                </div>
              </div>
              <div className="mt-6 flex items-center justify-end gap-3">
                <Button type="button" variant="outline" onClick={() => setIsFolderModalOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={createMutation.isPending || !folderName.trim()}>
                  Create Folder
                </Button>
              </div>
            </form>
        </AppModal>
      )}

      {/* Create / Edit Intent Modal */}
      {isModalOpen && (
        <AppModal
          title={editingIntent ? "Edit Classifier" : "Create Custom Intent Classifier"}
          description="Configure classifier keywords and enforcement action."
          onClose={() => setIsModalOpen(false)}
        >
          <Card className="border-0 bg-transparent shadow-none">
            <form onSubmit={handleSubmit}>
              <CardContent className="space-y-4 max-h-[70vh] overflow-y-auto">
                {folders.length > 0 && (
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Folder / Group</label>
                    <select
                      value={parentId || ""}
                      onChange={(e) => setParentId(e.target.value ? e.target.value : null)}
                      className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none"
                    >
                      <option value="">(No folder - Root)</option>
                      {folders.map((f) => (
                        <option key={f.id} value={f.id}>
                          📁 {f.name}
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                <div className="space-y-2">
                  <label className="text-sm font-medium">Classifier Name</label>
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none"
                    placeholder="e.g. Financial Wire Exfiltration"
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">Description</label>
                  <input
                    type="text"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none"
                    placeholder="Optional description"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Enforcement Action</label>
                    <select
                      value={action}
                      onChange={(e) => setAction(e.target.value as any)}
                      className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none"
                    >
                      <option value="block">Block</option>
                      <option value="redact">Redact</option>
                      <option value="monitor">Monitor</option>
                    </select>
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium">Confidence Threshold</label>
                    <input
                      type="number"
                      min="0.1"
                      max="1.0"
                      step="0.05"
                      value={confidenceThreshold}
                      onChange={(e) => setConfidenceThreshold(parseFloat(e.target.value))}
                      className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">Sample Phrases / Keywords</label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={newKeyword}
                      onChange={(e) => setNewKeyword(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          e.preventDefault();
                          handleAddKeyword();
                        }
                      }}
                      className="flex h-9 flex-1 rounded-md border border-input bg-background px-3 text-sm outline-none"
                      placeholder="Add phrase or keyword..."
                    />
                    <Button type="button" variant="secondary" onClick={handleAddKeyword}>
                      Add
                    </Button>
                  </div>

                  <div className="flex flex-wrap gap-1.5 pt-2 max-h-32 overflow-y-auto">
                    {keywords.map((kw) => (
                      <Badge key={kw} variant="secondary" className="gap-1 text-[10px] h-5">
                        {kw}
                        <button
                          type="button"
                          onClick={() => handleRemoveKeyword(kw)}
                          className="text-muted-foreground hover:text-foreground"
                        >
                          &times;
                        </button>
                      </Badge>
                    ))}
                  </div>
                </div>
              </CardContent>

              <div className="flex items-center justify-end gap-3 p-6 pt-2 border-t border-border/50">
                <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)}>
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={createMutation.isPending || updateMutation.isPending || !name.trim()}
                >
                  {editingIntent ? "Save Changes" : "Create Classifier"}
                </Button>
              </div>
            </form>
          </Card>
        </AppModal>
      )}

      {/* Tester Modal */}
      {isTesterModalOpen && (
        <CustomIntentTesterModal onClose={() => setIsTesterModalOpen(false)} />
      )}
    </div>
  );
}
