/** Compile-only proof: created and repeated responses both carry a thread ID. */
import type { SearchStartWantedResponseResponses } from '../../contracts/generated/types.gen';

const created: SearchStartWantedResponseResponses[201] = {
  conversation_id: '10000000-0000-4000-8000-000000000001', created: true,
};
const existing: SearchStartWantedResponseResponses[200] = {
  conversation_id: created.conversation_id, created: false,
};
const routeId: string = existing.conversation_id;
// @ts-expect-error A successful repeat without the conversation ID is invalid.
const missingId: SearchStartWantedResponseResponses[200] = { created: false };
void [created, existing, routeId, missingId];
