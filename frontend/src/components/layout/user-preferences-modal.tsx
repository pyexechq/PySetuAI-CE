import { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { usePreferencesStore } from "@/stores/preferences-store";
import { useAuthStore } from "@/stores/auth-store";
import { api } from "@/lib/api";

interface UserPreferencesModalProps {
  isOpen: boolean;
  onClose: () => void;
  user: any;
}

export function UserPreferencesModal({ isOpen, onClose, user }: UserPreferencesModalProps) {
  const globalTimezone = usePreferencesStore((s) => s.timezone);
  const setGlobalTimezone = usePreferencesStore((s) => s.setTimezone);
  const updateUser = useAuthStore((s) => s.updateUser);
  const token = useAuthStore((s) => s.token);
  const [localTimezone, setLocalTimezone] = useState(globalTimezone);
  const [firstName, setFirstName] = useState(user?.name?.split(" ")[0] || "");
  const [lastName, setLastName] = useState(user?.name?.split(" ").slice(1).join(" ") || "");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [mounted, setMounted] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (isOpen) {
      setFirstName(user?.name?.split(" ")[0] || "");
      setLastName(user?.name?.split(" ").slice(1).join(" ") || "");
      setLocalTimezone(globalTimezone);
    }
  }, [isOpen, user?.name, globalTimezone]);

  if (!isOpen || !mounted) return null;

  const handleSave = async () => {
    setGlobalTimezone(localTimezone);
    const updatedName = [firstName, lastName].filter(Boolean).join(" ");
    
    if (updatedName !== user?.name) {
      if (token) {
        setIsSaving(true);
        try {
          await api.updateCurrentUser(token, { name: updatedName });
          updateUser({ name: updatedName });
        } catch (err) {
          console.error("Failed to update profile", err);
        } finally {
          setIsSaving(false);
        }
      } else {
        updateUser({ name: updatedName });
      }
    }
    onClose();
  };


  const modalContent = (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-md max-h-[90vh] overflow-y-auto rounded-lg border border-border bg-card p-6 shadow-lg animate-in fade-in-90 zoom-in-95">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">User Preferences</h2>
          <button onClick={onClose} className="rounded-full p-1 hover:bg-muted transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>
        
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium leading-none">First Name</label>
              <input 
                type="text" 
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium leading-none">Last Name</label>
              <input 
                type="text" 
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              />
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium leading-none">Timezone</label>
            <select 
              value={localTimezone}
              onChange={(e) => setLocalTimezone(e.target.value)}
              className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring [&>option]:bg-background"
            >
              <option value="browser">Browser Default (Local)</option>
              <option value="UTC">UTC</option>
              <option value="America/New_York">Eastern Time (ET)</option>
              <option value="America/Chicago">Central Time (CT)</option>
              <option value="America/Denver">Mountain Time (MT)</option>
              <option value="America/Los_Angeles">Pacific Time (PT)</option>
              <option value="Asia/Kolkata">India Standard Time (IST)</option>
            </select>
          </div>

          <div className="pt-4 border-t border-border mt-4">
            <h3 className="text-sm font-medium mb-3">Change Password</h3>
            <div className="space-y-3">
              <div className="space-y-2">
                <label className="text-xs text-muted-foreground">Current Password</label>
                <input 
                  type="password" 
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs text-muted-foreground">New Password</label>
                <input 
                  type="password" 
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                />
              </div>
            </div>
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-2">
          <Button variant="outline" onClick={onClose} disabled={isSaving}>Cancel</Button>
          <Button onClick={handleSave} disabled={isSaving}>
            {isSaving ? "Saving..." : "Save Changes"}
          </Button>
        </div>
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
}
