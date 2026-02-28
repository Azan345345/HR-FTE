import { useState, useEffect } from "react";
import {
  Settings,
  Search,
  FileText,
  Mail,
  Target,
  Pause,
  BarChart,
  ClipboardList,
  DollarSign,
  Briefcase,
  PlusCircle,
  MessageSquare,
  Eye,
  Clock
} from "lucide-react";

import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";

interface CommandPaletteProps {
  onOpenSettings: () => void;
  onViewChange: (view: any) => void;
  onSessionChange: (id: string | null) => void;
  recentSessions: any[];
}

export function CommandPalette({
  onOpenSettings,
  onViewChange,
  onSessionChange,
  recentSessions
}: CommandPaletteProps) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((open) => !open);
      }
    };

    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  const runCommand = (action: () => void) => {
    action();
    setOpen(false);
  };

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput placeholder="Type a command or search..." />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>
        <CommandGroup heading="QUICK ACTIONS">
          <CommandItem onSelect={() => runCommand(() => {
            onViewChange("chat");
            onSessionChange(null);
          })}>
            <PlusCircle className="mr-2 h-4 w-4" />
            <span>New Conversation</span>
          </CommandItem>
          <CommandItem onSelect={() => runCommand(onOpenSettings)}>
            <Settings className="mr-2 h-4 w-4" />
            <span>Open Settings</span>
          </CommandItem>
          <CommandItem onSelect={() => runCommand(() => onViewChange("jobs"))}>
            <Search className="mr-2 h-4 w-4" />
            <span>Search for new jobs</span>
          </CommandItem>
        </CommandGroup>
        <CommandSeparator />
        <CommandGroup heading="NAVIGATION">
          <CommandItem onSelect={() => runCommand(() => onViewChange("chat"))}>
            <MessageSquare className="mr-2 h-4 w-4" />
            <span>Go to Chat</span>
          </CommandItem>
          <CommandItem onSelect={() => runCommand(() => onViewChange("jobs"))}>
            <Briefcase className="mr-2 h-4 w-4" />
            <span>Go to Application Tracker</span>
          </CommandItem>
          <CommandItem onSelect={() => runCommand(() => onViewChange("observability"))}>
            <BarChart className="mr-2 h-4 w-4" />
            <span>Go to Observability</span>
          </CommandItem>
        </CommandGroup>
        <CommandSeparator />
        {recentSessions.length > 0 && (
          <CommandGroup heading="RECENT CHATS">
            {recentSessions.map((session) => (
              <CommandItem
                key={session.session_id}
                onSelect={() => runCommand(() => {
                  onViewChange("chat");
                  onSessionChange(session.session_id);
                })}
              >
                <Clock className="mr-2 h-4 w-4" />
                <span className="truncate">{session.title || "Untitled Chat"}</span>
              </CommandItem>
            ))}
          </CommandGroup>
        )}
      </CommandList>
    </CommandDialog>
  );
}
