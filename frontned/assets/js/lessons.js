/* Lesson list + offline starter content.
   With the backend on, lesson.html asks the AI to write each lesson fresh. */
window.LESSONS = [
  {
    id: 'warning-signs', title: 'Spot the warning signs', minutes: 5, tile: 'tile--coral',
    svg: '<path d="M12 9v4M12 17h.01M10.3 3.9L2.5 17.5A2 2 0 004.2 20.5h15.6a2 2 0 001.7-3L13.7 3.9a2 2 0 00-3.4 0z"/>',
    intro: 'Abuse rarely starts with violence. It often starts small, with control that is easy to mistake for care.',
    points: [
      { title: 'They decide who you see', body: 'Slowly cutting you off from friends and family, or making you feel guilty for spending time with them.' },
      { title: 'They check your phone or money', body: 'Needing your passwords, reading your messages, or controlling what you spend.' },
      { title: 'Jealousy is called love', body: 'Anger when you are away, explained as "I just care about you".' },
      { title: 'You feel afraid', body: 'Threats, breaking things, or always "walking on eggshells" around them.' },
    ],
    takeaway: 'Abuse is never your fault. If this sounds familiar, the GBV Command Centre is free and open 24/7 on 0800 428 428.',
  },
  {
    id: 'consent', title: 'Consent, explained', minutes: 4, tile: 'tile--blue',
    svg: '<path d="M12 20s-7-4.5-7-10a4 4 0 017-2.6A4 4 0 0119 10c0 5.5-7 10-7 10z"/>',
    intro: 'Consent means everyone involved freely and clearly agrees. Anything less is not consent.',
    points: [
      { title: 'It is a clear, free yes', body: 'Silence, pressure or "not saying no" is not a yes.' },
      { title: 'You can change your mind', body: 'Saying yes earlier does not mean yes now. You can stop at any time.' },
      { title: 'Some people cannot consent', body: 'Someone asleep, very drunk, drugged or under 16 cannot give consent.' },
      { title: 'Relationships are not consent', body: 'Being married or dating does not mean someone always agrees.' },
    ],
    takeaway: 'Respecting a no is part of loving someone.',
  },
  {
    id: 'help-a-friend', title: 'How to help a friend', minutes: 0, live: true, tile: 'tile--amber',
    svg: '<circle cx="9" cy="8" r="3"/><circle cx="17" cy="9" r="2.5"/><path d="M3 20a6 6 0 0112 0M14 20a4.5 4.5 0 017 0"/>',
  },
  {
    id: 'safety-plan', title: 'Make a safety plan', minutes: 6, tile: 'tile--green',
    svg: '<path d="M9 11l3 3 8-8"/><path d="M20 12v7a2 2 0 01-2 2H6a2 2 0 01-2-2V5a2 2 0 012-2h9"/>',
    intro: 'A safety plan is what you will do if you need to leave quickly. Planning ahead makes it easier when the moment comes.',
    points: [
      { title: 'Keep documents together', body: 'ID, birth certificates and bank cards in one place, or copies with someone you trust.' },
      { title: 'Agree a code word', body: 'Pick a word that tells a friend or family member to call for help.' },
      { title: 'Know where you will go', body: 'A friend, family member or shelter, and how you will get there.' },
      { title: 'Protection orders are free', body: 'You can apply at your nearest magistrate\'s court. Someone can go with you.' },
    ],
    takeaway: 'Set your safe word and trusted contacts in Lerato Alert as part of your plan.',
  },
  {
    id: 'healthy-love', title: 'What healthy love looks like', minutes: 4, tile: 'tile--purple',
    svg: '<circle cx="8" cy="12" r="4"/><circle cx="16" cy="12" r="4"/>',
    intro: 'Lerato means love. Healthy love makes you feel safe, not small.',
    points: [
      { title: 'Respect for your choices', body: 'Your partner accepts your opinions, friends and decisions.' },
      { title: 'Trust without checking', body: 'No tracking, phone searches or demands to prove where you were.' },
      { title: 'Safe disagreements', body: 'You can argue without fear, threats or being punished.' },
      { title: 'Room to grow', body: 'They support your work, studies and dreams.' },
    ],
    takeaway: 'You deserve love that never hurts.',
  },
];
