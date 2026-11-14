import type { ConversationListItem } from "./api/conversations";

type ContactIdentity = Pick<
  ConversationListItem,
  "student_id" | "student_phone" | "whatsapp_user_id" | "display_name"
>;

/** Display only: these labels must never be used to resolve or link contacts. */
export function contactIdentityLabel(contact: ContactIdentity): string {
  if (contact.student_phone) return contact.student_phone;
  if (contact.whatsapp_user_id) return `WhatsApp ID: ${contact.whatsapp_user_id}`;
  return `Contacto #${contact.student_id}`;
}

export function contactDisplayName(
  contact: ContactIdentity,
  profileName?: string | null,
): string {
  return (
    profileName?.trim() || contact.display_name?.trim() || contactIdentityLabel(contact)
  );
}

export function contactInitials(
  contact: ContactIdentity,
  profileName?: string | null,
): string {
  const name = profileName?.trim() || contact.display_name?.trim();
  if (name) {
    const parts = name.split(/\s+/);
    return (parts[0][0] + (parts[1]?.[0] ?? "")).toUpperCase();
  }
  // Only actual phones have numeric initials; preserve opaque WhatsApp IDs.
  return contact.student_phone?.replace(/\D/g, "").slice(-2) || "WA";
}
