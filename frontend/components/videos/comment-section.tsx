"use client";

import { useState, useRef, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ThumbsUp, ThumbsDown, ChevronDown, ChevronUp, Loader2, Send, Github } from "lucide-react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import type { Comment } from "@/lib/types";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "たった今";
  if (mins < 60) return `${mins}分前`;
  const h = Math.floor(mins / 60);
  if (h < 24) return `${h}時間前`;
  const d = Math.floor(h / 24);
  if (d < 30) return `${d}日前`;
  const mo = Math.floor(d / 30);
  if (mo < 12) return `${mo}ヶ月前`;
  return `${Math.floor(mo / 12)}年前`;
}

function getInitials(name: string): string {
  return name.split(/\s+/).map((n) => n[0]).join("").slice(0, 2).toUpperCase();
}

const AVATAR_COLORS = [
  "bg-blue-500", "bg-green-500", "bg-yellow-500", "bg-purple-500",
  "bg-pink-500", "bg-indigo-500", "bg-red-500", "bg-teal-500",
];

function avatarColor(userId: string): string {
  let hash = 0;
  for (const c of userId) hash = (hash * 31 + c.charCodeAt(0)) % AVATAR_COLORS.length;
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

// ---------------------------------------------------------------------------
// Avatar
// ---------------------------------------------------------------------------

function Avatar({ userId, displayName, size = "md" }: { userId: string; displayName: string; size?: "sm" | "md" }) {
  const sizeClass = size === "sm" ? "size-8 text-xs" : "size-10 text-sm";
  return (
    <div className={cn(
      "rounded-full flex items-center justify-center text-white font-semibold shrink-0",
      sizeClass,
      avatarColor(userId),
    )}>
      {getInitials(displayName)}
    </div>
  );
}

// ---------------------------------------------------------------------------
// CommentInput
// ---------------------------------------------------------------------------

interface CommentInputProps {
  videoId: string;
  parentId?: string;
  placeholder?: string;
  onSuccess?: () => void;
  autoFocus?: boolean;
  compact?: boolean;
}

function CommentInput({ videoId, parentId, placeholder, onSuccess, autoFocus, compact }: CommentInputProps) {
  const [text, setText] = useState("");
  const [focused, setFocused] = useState(autoFocus ?? false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () => api.createComment(videoId, { text: text.trim(), parentId }),
    onSuccess: () => {
      setText("");
      setFocused(false);
      queryClient.invalidateQueries({ queryKey: ["comments", videoId] });
      onSuccess?.();
    },
  });

  useEffect(() => {
    if (autoFocus && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [autoFocus]);

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey) && text.trim()) {
      mutation.mutate();
    }
  }

  const currentUser =
    typeof window !== "undefined" ? localStorage.getItem("user_display_name") ?? "ゲスト" : "ゲスト";
  const currentUserId =
    typeof window !== "undefined" ? localStorage.getItem("user_id") ?? "guest" : "guest";

  return (
    <div className={cn("flex gap-3", compact ? "gap-2" : "")}>
      <div className="relative shrink-0">
        <Avatar userId={currentUserId} displayName={currentUser} size={compact ? "sm" : "md"} />
        <span className="absolute -bottom-1 -right-1 flex size-4 items-center justify-center rounded-full bg-[#0f0f0f] dark:bg-[#f1f1f1]">
          <Github className="size-2.5 text-white dark:text-[#0f0f0f]" />
        </span>
      </div>
      <div className="flex-1 min-w-0">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onFocus={() => setFocused(true)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder ?? "コメントを追加..."}
          rows={focused ? 3 : 1}
          className={cn(
            "w-full resize-none bg-transparent text-sm text-[#0f0f0f] dark:text-[#f1f1f1]",
            "border-b border-[#ccc] dark:border-[#3f3f3f] outline-none",
            "placeholder:text-[#606060] dark:placeholder:text-[#909090]",
            "transition-all focus:border-[#0f0f0f] dark:focus:border-[#f1f1f1]",
            compact ? "text-xs" : "text-sm",
          )}
        />
        {focused && (
          <div className="flex justify-end gap-2 mt-2">
            <button
              type="button"
              onClick={() => { setText(""); setFocused(false); }}
              className="px-4 py-1.5 text-sm font-medium text-[#0f0f0f] dark:text-[#f1f1f1] rounded-full hover:bg-[#f2f2f2] dark:hover:bg-[#272727] transition-colors"
            >
              キャンセル
            </button>
            <button
              type="button"
              onClick={() => mutation.mutate()}
              disabled={!text.trim() || mutation.isPending}
              className={cn(
                "flex items-center gap-1.5 px-4 py-1.5 text-sm font-medium rounded-full transition-colors",
                text.trim()
                  ? "bg-[#065fd4] dark:bg-[#3ea6ff] text-white dark:text-[#0f0f0f] hover:bg-[#0552bb]"
                  : "bg-[#f2f2f2] dark:bg-[#272727] text-[#909090] cursor-not-allowed",
              )}
            >
              {mutation.isPending ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <Send className="size-3.5" />
              )}
              コメント
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// CommentReplyItem
// ---------------------------------------------------------------------------

function CommentReplyItem({ comment, videoId }: { comment: Comment; videoId: string }) {
  const queryClient = useQueryClient();

  const likeMutation = useMutation({
    mutationFn: () => api.toggleCommentLike(comment.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["comments", videoId] });
    },
  });

  return (
    <div className="flex gap-3">
      <div className="relative shrink-0">
        <Avatar userId={comment.userId} displayName={comment.displayName} size="sm" />
        <span className="absolute -bottom-1 -right-1 flex size-4 items-center justify-center rounded-full bg-[#0f0f0f] dark:bg-[#f1f1f1]">
          <Github className="size-2.5 text-white dark:text-[#0f0f0f]" />
        </span>
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-[#0f0f0f] dark:text-[#f1f1f1]">
            @{comment.displayName}
          </span>
          <span className="text-xs text-[#606060] dark:text-[#909090]">
            {timeAgo(comment.createdAt)}
          </span>
        </div>
        <p className="text-sm text-[#0f0f0f] dark:text-[#f1f1f1] mt-1 leading-relaxed whitespace-pre-wrap">
          {comment.text}
        </p>
        <div className="flex items-center gap-1 mt-2">
          <button
            onClick={() => likeMutation.mutate()}
            className="flex items-center gap-1 px-2 py-1 rounded-full hover:bg-[#f2f2f2] dark:hover:bg-[#272727] transition-colors"
          >
            <ThumbsUp className={cn(
              "size-3.5",
              comment.likedByMe ? "text-[#065fd4] dark:text-[#3ea6ff] fill-current" : "text-[#606060] dark:text-[#909090]"
            )} />
            {comment.likeCount > 0 && (
              <span className="text-xs text-[#606060] dark:text-[#909090]">{comment.likeCount}</span>
            )}
          </button>
          <button className="p-1 rounded-full hover:bg-[#f2f2f2] dark:hover:bg-[#272727] transition-colors">
            <ThumbsDown className="size-3.5 text-[#606060] dark:text-[#909090]" />
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// CommentItem
// ---------------------------------------------------------------------------

function CommentItem({ comment, videoId }: { comment: Comment; videoId: string }) {
  const [showReplies, setShowReplies] = useState(false);
  const [showReplyInput, setShowReplyInput] = useState(false);
  const queryClient = useQueryClient();
  const replyCount = comment.replies?.length ?? 0;

  const likeMutation = useMutation({
    mutationFn: () => api.toggleCommentLike(comment.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["comments", videoId] });
    },
  });

  return (
    <div className="flex gap-3">
      <div className="relative shrink-0">
        <Avatar userId={comment.userId} displayName={comment.displayName} />
        <span className="absolute -bottom-1 -right-1 flex size-4 items-center justify-center rounded-full bg-[#0f0f0f] dark:bg-[#f1f1f1]">
          <Github className="size-2.5 text-white dark:text-[#0f0f0f]" />
        </span>
      </div>
      <div className="flex-1 min-w-0">
        {/* Header */}
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-[#0f0f0f] dark:text-[#f1f1f1]">
            @{comment.displayName}
          </span>
          <span className="text-xs text-[#606060] dark:text-[#909090]">
            {timeAgo(comment.createdAt)}
          </span>
        </div>

        {/* Text */}
        <p className="text-sm text-[#0f0f0f] dark:text-[#f1f1f1] mt-1 leading-relaxed whitespace-pre-wrap">
          {comment.text}
        </p>

        {/* Actions */}
        <div className="flex items-center gap-1 mt-2">
          <button
            onClick={() => likeMutation.mutate()}
            className="flex items-center gap-1.5 px-2 py-1.5 rounded-full hover:bg-[#f2f2f2] dark:hover:bg-[#272727] transition-colors"
          >
            <ThumbsUp className={cn(
              "size-4",
              comment.likedByMe ? "text-[#065fd4] dark:text-[#3ea6ff] fill-current" : "text-[#606060] dark:text-[#909090]"
            )} />
            {comment.likeCount > 0 && (
              <span className="text-xs text-[#606060] dark:text-[#909090]">{comment.likeCount}</span>
            )}
          </button>
          <button className="p-1.5 rounded-full hover:bg-[#f2f2f2] dark:hover:bg-[#272727] transition-colors">
            <ThumbsDown className="size-4 text-[#606060] dark:text-[#909090]" />
          </button>
          <button
            onClick={() => setShowReplyInput((v) => !v)}
            className="px-3 py-1.5 text-xs font-semibold text-[#0f0f0f] dark:text-[#f1f1f1] rounded-full hover:bg-[#f2f2f2] dark:hover:bg-[#272727] transition-colors"
          >
            返信
          </button>
        </div>

        {/* Reply input */}
        {showReplyInput && (
          <div className="mt-3">
            <CommentInput
              videoId={videoId}
              parentId={comment.id}
              placeholder="返信を追加..."
              compact
              autoFocus
              onSuccess={() => {
                setShowReplyInput(false);
                setShowReplies(true);
              }}
            />
          </div>
        )}

        {/* Replies toggle */}
        {replyCount > 0 && (
          <button
            onClick={() => setShowReplies((v) => !v)}
            className="flex items-center gap-1.5 mt-3 px-3 py-1.5 text-sm font-semibold text-[#065fd4] dark:text-[#3ea6ff] rounded-full hover:bg-[#065fd4]/10 dark:hover:bg-[#3ea6ff]/10 transition-colors"
          >
            {showReplies ? (
              <ChevronUp className="size-4" />
            ) : (
              <ChevronDown className="size-4" />
            )}
            {replyCount}件の返信
          </button>
        )}

        {/* Replies list */}
        {showReplies && comment.replies && (
          <div className="mt-3 space-y-4 pl-0">
            {comment.replies.map((reply) => (
              <CommentReplyItem key={reply.id} comment={reply} videoId={videoId} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// CommentSection (main export)
// ---------------------------------------------------------------------------

type SortKey = "top" | "new";

export function CommentSection({ videoId }: { videoId: string }) {
  const [sort, setSort] = useState<SortKey>("top");
  const [showSortMenu, setShowSortMenu] = useState(false);
  const sortMenuRef = useRef<HTMLDivElement>(null);

  const { data: rawComments = [], isLoading } = useQuery({
    queryKey: ["comments", videoId],
    queryFn: () => api.getComments(videoId),
    staleTime: 30000,
  });

  const sortedComments = [...rawComments].sort((a, b) => {
    if (sort === "top") return b.likeCount - a.likeCount;
    return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
  });

  const totalCount = rawComments.reduce((acc, c) => acc + 1 + (c.replies?.length ?? 0), 0);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (sortMenuRef.current && !sortMenuRef.current.contains(e.target as Node)) {
        setShowSortMenu(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  return (
    <div className="mt-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-6">
        <h2 className="flex items-center gap-2 text-base font-semibold text-[#0f0f0f] dark:text-[#f1f1f1]">
          <Github className="size-4 text-[#606060] dark:text-[#909090]" />
          {isLoading ? "コメント" : `${totalCount}件のコメント`}
        </h2>
        <div className="relative" ref={sortMenuRef}>
          <button
            onClick={() => setShowSortMenu((v) => !v)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-semibold text-[#0f0f0f] dark:text-[#f1f1f1] rounded-full hover:bg-[#f2f2f2] dark:hover:bg-[#272727] transition-colors"
          >
            <svg className="size-4" viewBox="0 0 24 24" fill="currentColor">
              <path d="M21 6H3V4h18v2zm-6 4H3v2h12v-2zm-6 6H3v2h6v-2z" />
            </svg>
            並べ替え
          </button>
          {showSortMenu && (
            <div className="absolute left-0 top-full mt-1 w-40 bg-white dark:bg-[#212121] border border-[#e5e5e5] dark:border-[#3f3f3f] rounded-xl shadow-lg py-2 z-20">
              {(["top", "new"] as SortKey[]).map((key) => (
                <button
                  key={key}
                  onClick={() => { setSort(key); setShowSortMenu(false); }}
                  className={cn(
                    "w-full text-left px-4 py-2.5 text-sm transition-colors",
                    sort === key
                      ? "font-semibold text-[#0f0f0f] dark:text-[#f1f1f1]"
                      : "text-[#606060] dark:text-[#909090] hover:bg-[#f2f2f2] dark:hover:bg-[#272727]"
                  )}
                >
                  {key === "top" ? "上位のコメント" : "新しい順"}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Input */}
      <CommentInput videoId={videoId} />

      {/* List */}
      {isLoading ? (
        <div className="flex justify-center py-10">
          <Loader2 className="size-6 animate-spin text-[#606060] dark:text-[#909090]" />
        </div>
      ) : sortedComments.length === 0 ? (
        <p className="text-sm text-[#606060] dark:text-[#909090] py-8 text-center">
          まだコメントがありません。最初のコメントを投稿してみましょう！
        </p>
      ) : (
        <div className="space-y-6">
          {sortedComments.map((comment) => (
            <CommentItem key={comment.id} comment={comment} videoId={videoId} />
          ))}
        </div>
      )}
    </div>
  );
}
