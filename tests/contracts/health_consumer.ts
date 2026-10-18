/** Compile-only consumer of generated request/response types; makes no request. */
import type {
  HealthHealthGetData,
  HealthHealthGetResponses,
  HealthResponse,
} from '../../contracts/generated/types.gen';

const response: HealthResponse = { status: 'ok' };
const success: HealthHealthGetResponses[200] = response;
const request: HealthHealthGetData = { url: '/health' };
void [response, success, request];
