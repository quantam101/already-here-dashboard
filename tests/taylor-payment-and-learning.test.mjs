import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const paymentHelper = readFileSync(new URL('../lib/stripe-hosted-payments.ts', import.meta.url), 'utf8');
const paymentRoute = readFileSync(new URL('../app/api/taylor/create-hosted-payment/route.ts', import.meta.url), 'utf8');
const learningRoute = readFileSync(new URL('../app/api/taylor/learning-record/route.ts', import.meta.url), 'utf8');
const conversationDoc = readFileSync(new URL('../docs/taylor-conversation-learning-and-deposits.md', import.meta.url), 'utf8');

assert.match(paymentHelper, /STRIPE_SECRET_KEY/);
assert.match(paymentHelper, /checkout\/sessions/);
assert.match(paymentHelper, /service_deposit/);
assert.match(paymentHelper, /project_down_payment/);
assert.match(paymentHelper, /retainer_activation/);
assert.match(paymentHelper, /dispatch_reservation/);
assert.match(paymentHelper, /parts_deposit/);
assert.match(paymentHelper, /success_url/);
assert.match(paymentHelper, /cancel_url/);
assert.match(paymentHelper, /client_reference_id/);
assert.match(paymentHelper, /metadata\[purpose\]/);

assert.match(paymentRoute, /createStripeCheckoutSession/);
assert.match(paymentRoute, /hostedPaymentUrl/);
assert.match(paymentRoute, /taylorSpokenResponse/);
assert.match(paymentRoute, /secure Stripe payment link/);

assert.match(learningRoute, /TaylorLearningRecord/);
assert.match(learningRoute, /operatorReviewRequired/);
assert.match(learningRoute, /requiresOperatorReview/);
assert.match(learningRoute, /redacted-number/);
assert.match(learningRoute, /redacted-code/);
assert.match(learningRoute, /pricing/);
assert.match(learningRoute, /refund/);
assert.match(learningRoute, /technician assignment/);

assert.match(conversationDoc, /Taylor should become more prepared after every conversation/);
assert.match(conversationDoc, /service deposit/);
assert.match(conversationDoc, /down payment/);
