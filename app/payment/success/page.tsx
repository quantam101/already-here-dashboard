type PaymentSuccessSearchParams = Promise<{ session_id?: string }>;

export default async function PaymentSuccessPage({ searchParams }: { searchParams: PaymentSuccessSearchParams }) {
  const params = await searchParams;

  return (
    <main className="shell">
      <section className="panel">
        <p className="eyebrow">Already Here LLC</p>
        <h1>Payment Submitted</h1>
        <p className="subhead">Stripe received the payment submission. Already Here LLC will confirm the final paid status after secure verification.</p>
        {params.session_id && <p className="detail"><strong>Session reference</strong><span>{params.session_id}</span></p>}
      </section>
    </main>
  );
}
