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
import { Sparkles } from "lucide-react";

const CONTENT_TYPE_OPTIONS = [
  { value: "blog", label: "Blog Post" },
  { value: "social", label: "Social Media" },
  { value: "email", label: "Email" },
  { value: "proposal", label: "Proposal" },
];

const TONE_OPTIONS = [
  { value: "professional", label: "Professional" },
  { value: "casual", label: "Casual" },
  { value: "technical", label: "Technical" },
  { value: "persuasive", label: "Persuasive" },
];

const LENGTH_OPTIONS = [
  { value: "short", label: "Short" },
  { value: "medium", label: "Medium" },
  { value: "long", label: "Long" },
];

export default function ContentGenerateDialog({
  open,
  onOpenChange,
  formData,
  setFormData,
  onSubmit,
  isGenerating,
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button className="flex items-center gap-2" data-testid="generate-content-btn">
          <Sparkles className="w-4 h-4" />
          Generate Content
        </Button>
      </DialogTrigger>
      <DialogContent data-testid="generate-content-dialog">
        <DialogHeader>
          <DialogTitle>Generate AI Content</DialogTitle>
        </DialogHeader>
        <form onSubmit={onSubmit} className="space-y-4">
          <SelectField
            label="Content Type"
            value={formData.content_type}
            onChange={(v) => setFormData((p) => ({ ...p, content_type: v }))}
            options={CONTENT_TYPE_OPTIONS}
            testId="content-type-select"
          />
          <TextField
            label="Topic"
            id="topic"
            value={formData.topic}
            onChange={(v) => setFormData((p) => ({ ...p, topic: v }))}
            placeholder="What should this content be about?"
            testId="content-topic-input"
            required
          />
          <div className="grid grid-cols-2 gap-4">
            <SelectField
              label="Tone"
              value={formData.tone}
              onChange={(v) => setFormData((p) => ({ ...p, tone: v }))}
              options={TONE_OPTIONS}
            />
            <SelectField
              label="Length"
              value={formData.length}
              onChange={(v) => setFormData((p) => ({ ...p, length: v }))}
              options={LENGTH_OPTIONS}
            />
          </div>
          <TextField
            label="Keywords (comma-separated)"
            id="keywords"
            value={formData.keywords}
            onChange={(v) => setFormData((p) => ({ ...p, keywords: v }))}
            placeholder="keyword1, keyword2, keyword3"
            testId="content-keywords-input"
          />
          <Button
            type="submit"
            className="w-full"
            disabled={isGenerating}
            data-testid="submit-content-btn"
          >
            {isGenerating ? "Generating..." : "Generate with AI"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function TextField({ label, id, value, onChange, placeholder, testId, required }) {
  return (
    <div>
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        required={required}
        data-testid={testId}
      />
    </div>
  );
}

function SelectField({ label, value, onChange, options, testId }) {
  return (
    <div>
      <Label>{label}</Label>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger data-testid={testId}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {options.map((opt) => (
            <SelectItem key={opt.value} value={opt.value}>
              {opt.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
