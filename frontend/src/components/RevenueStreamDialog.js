import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Plus } from "lucide-react";

const STREAM_TYPES = [
  { value: "affiliate", label: "Affiliate" },
  { value: "service", label: "Service" },
  { value: "content", label: "Content" },
  { value: "proposal", label: "Proposal" },
];

export default function RevenueStreamDialog({ open, onOpenChange, formData, onChange, onSubmit }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button className="flex items-center gap-2" data-testid="create-revenue-btn">
          <Plus className="w-4 h-4" />
          New Stream
        </Button>
      </DialogTrigger>
      <DialogContent data-testid="create-revenue-dialog">
        <DialogHeader>
          <DialogTitle>Create Revenue Stream</DialogTitle>
        </DialogHeader>
        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <Label htmlFor="name">Stream Name</Label>
            <Input
              id="name"
              name="name"
              value={formData.name}
              onChange={onChange}
              placeholder="e.g., Affiliate Marketing"
              required
              data-testid="revenue-name-input"
            />
          </div>
          <div>
            <Label htmlFor="type">Type</Label>
            <Select value={formData.type} onValueChange={(v) => onChange({ target: { name: "type", value: v } })}>
              <SelectTrigger data-testid="revenue-type-select">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {STREAM_TYPES.map((t) => (
                  <SelectItem key={t.value} value={t.value}>
                    {t.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label htmlFor="monthly_target">Monthly Target ($)</Label>
            <Input
              id="monthly_target"
              name="monthly_target"
              type="number"
              value={formData.monthly_target}
              onChange={onChange}
              placeholder="0"
              data-testid="revenue-target-input"
            />
          </div>
          <div>
            <Label htmlFor="description">Description</Label>
            <Input
              id="description"
              name="description"
              value={formData.description}
              onChange={onChange}
              placeholder="Brief description"
              data-testid="revenue-description-input"
            />
          </div>
          <Button type="submit" className="w-full" data-testid="submit-revenue-btn">
            Create Stream
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
